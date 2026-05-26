"""ComfyUI HTTP API client."""
from __future__ import annotations

import copy
import re
import time
from pathlib import Path
from typing import Any

import httpx


class ComfyError(Exception):
    """Base exception for ComfyUI errors."""


class ComfyConnectionError(ComfyError):
    """ComfyUI server is unreachable."""


class ComfyTimeoutError(ComfyError):
    """Generation did not complete within the timeout."""


_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")


def _substitute(obj: Any, params: dict[str, Any]) -> Any:
    """Recursively replace {{key}} placeholders in a workflow structure.

    A string that is *entirely* one token (e.g. ``"{{seed}}"``") is replaced
    with the raw param value — preserving int/float types for ComfyUI.
    Mixed strings (e.g. ``"prefix_{{name}}"``") are string-interpolated.
    """
    if isinstance(obj, dict):
        return {k: _substitute(v, params) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, params) for v in obj]
    if isinstance(obj, str):
        full = _TEMPLATE_RE.fullmatch(obj)
        if full:
            return params.get(full.group(1), obj)
        return _TEMPLATE_RE.sub(lambda m: str(params.get(m.group(1), m.group(0))), obj)
    return obj


class ComfyClient:
    """Thin wrapper around the ComfyUI HTTP API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=30.0)

    # ── Template injection ────────────────────────────────────────────────────

    def inject_params(self, workflow: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Return a deep copy of *workflow* with ``{{key}}`` placeholders substituted."""
        return _substitute(copy.deepcopy(workflow), params)

    # ── API calls ─────────────────────────────────────────────────────────────

    def submit_workflow(self, workflow_api: dict[str, Any]) -> str:
        """POST *workflow_api* to ``/prompt`` and return the ``prompt_id``.

        Strips ``_meta`` keys before sending so ComfyUI doesn't reject them.
        """
        clean = {k: v for k, v in workflow_api.items() if not k.startswith("_")}
        try:
            resp = self._http.post(f"{self.base_url}/prompt", json={"prompt": clean})
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise ComfyConnectionError(
                f"Cannot reach ComfyUI at {self.base_url}. "
                "Is it running? Check COMFYUI_URL in .env."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ComfyError(
                f"ComfyUI rejected the workflow (HTTP {exc.response.status_code}): "
                f"{exc.response.text}"
            ) from exc

        return str(resp.json()["prompt_id"])

    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> dict[str, Any]:
        """Poll ``/history/{prompt_id}`` until completion or *timeout* seconds."""
        deadline = time.monotonic() + timeout
        interval = 1.0

        while time.monotonic() < deadline:
            try:
                resp = self._http.get(f"{self.base_url}/history/{prompt_id}")
                resp.raise_for_status()
            except httpx.ConnectError as exc:
                raise ComfyConnectionError(
                    f"Lost connection to ComfyUI at {self.base_url}."
                ) from exc

            data = resp.json()
            if prompt_id in data:
                entry: dict[str, Any] = data[prompt_id]
                status = entry.get("status", {})
                status_str = status.get("status_str", "")
                if status.get("completed") or status_str == "success":
                    return entry
                if status_str == "error":
                    msgs = status.get("messages", [])
                    raise ComfyError(f"Generation failed: {msgs}")

            time.sleep(interval)
            interval = min(interval * 1.5, 5.0)

        raise ComfyTimeoutError(
            f"Generation {prompt_id} did not finish within {timeout}s. "
            "Increase imagegen.timeout_sec in config/pipeline.yaml."
        )

    def download_outputs(self, prompt_id: str, output_dir: Path) -> list[Path]:
        """Download all output images for *prompt_id* into *output_dir*."""
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            resp = self._http.get(f"{self.base_url}/history/{prompt_id}")
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise ComfyConnectionError(str(exc)) from exc

        entry = resp.json().get(prompt_id, {})
        saved: list[Path] = []

        for node_outputs in entry.get("outputs", {}).values():
            for img_info in node_outputs.get("images", []):
                filename: str = img_info["filename"]
                params: dict[str, str] = {
                    "filename": filename,
                    "type": img_info.get("type", "output"),
                }
                if subfolder := img_info.get("subfolder"):
                    params["subfolder"] = subfolder

                try:
                    img_resp = self._http.get(
                        f"{self.base_url}/view", params=params, timeout=60.0
                    )
                    img_resp.raise_for_status()
                except httpx.HTTPError as exc:
                    raise ComfyError(f"Failed to download {filename}: {exc}") from exc

                dest = output_dir / filename
                dest.write_bytes(img_resp.content)
                saved.append(dest)

        return saved

    # ── Context manager ───────────────────────────────────────────────────────

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ComfyClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
