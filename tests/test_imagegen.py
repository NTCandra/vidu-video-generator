"""Unit tests for ComfyUI client and batch generation."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_pipeline.imagegen.comfy_client import (
    ComfyClient,
    ComfyConnectionError,
    ComfyError,
    ComfyTimeoutError,
    _substitute,
)


# ── _substitute ───────────────────────────────────────────────────────────────

def test_substitute_string():
    assert _substitute("{{name}}", {"name": "hello"}) == "hello"

def test_substitute_preserves_int():
    assert _substitute("{{seed}}", {"seed": 42}) == 42

def test_substitute_preserves_float():
    assert _substitute("{{cfg}}", {"cfg": 6.5}) == 6.5

def test_substitute_mixed_string():
    result = _substitute("prefix_{{name}}", {"name": "world"})
    assert result == "prefix_world"

def test_substitute_missing_key_unchanged():
    assert _substitute("{{missing}}", {}) == "{{missing}}"

def test_substitute_nested_dict():
    workflow = {"node": {"inputs": {"text": "{{prompt}}", "seed": "{{seed}}"}}}
    result = _substitute(workflow, {"prompt": "hello", "seed": 7})
    assert result == {"node": {"inputs": {"text": "hello", "seed": 7}}}

def test_substitute_list():
    result = _substitute(["{{a}}", "{{b}}"], {"a": 1, "b": 2})
    assert result == [1, 2]

def test_substitute_link_array_untouched():
    # ComfyUI link arrays like ["4", 1] are plain strings/ints, not {{templates}}, so untouched
    result = _substitute(["4", 1], {"4": "should_not_replace"})
    assert result == ["4", 1]


# ── ComfyClient.inject_params ─────────────────────────────────────────────────

def test_inject_params_deep_copy():
    client = ComfyClient("http://localhost:8188")
    workflow = {"6": {"inputs": {"text": "{{prompt}}"}}}
    result = client.inject_params(workflow, {"prompt": "test"})
    assert result["6"]["inputs"]["text"] == "test"
    # Original unchanged
    assert workflow["6"]["inputs"]["text"] == "{{prompt}}"
    client.close()


# ── ComfyClient.submit_workflow ───────────────────────────────────────────────

def test_submit_workflow_success():
    client = ComfyClient("http://localhost:8188")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"prompt_id": "abc-123"}
    mock_resp.raise_for_status = MagicMock()

    with patch.object(client._http, "post", return_value=mock_resp) as mock_post:
        prompt_id = client.submit_workflow({"4": {"class_type": "CheckpointLoaderSimple", "inputs": {}}})

    assert prompt_id == "abc-123"
    call_json = mock_post.call_args.kwargs["json"]
    assert "prompt" in call_json
    # _meta should be stripped
    assert "_meta" not in call_json["prompt"]
    client.close()


def test_submit_workflow_strips_meta():
    client = ComfyClient("http://localhost:8188")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"prompt_id": "x"}
    mock_resp.raise_for_status = MagicMock()

    workflow = {
        "_meta": {"version": "1.0"},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {}},
    }
    with patch.object(client._http, "post", return_value=mock_resp) as mock_post:
        client.submit_workflow(workflow)

    sent = mock_post.call_args.kwargs["json"]["prompt"]
    assert "_meta" not in sent
    assert "4" in sent
    client.close()


def test_submit_workflow_connection_error():
    import httpx

    client = ComfyClient("http://localhost:9999")
    with patch.object(client._http, "post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(ComfyConnectionError, match="Cannot reach ComfyUI"):
            client.submit_workflow({})
    client.close()


# ── ComfyClient.wait_for_completion ──────────────────────────────────────────

def _mock_history_response(prompt_id: str, status_str: str, completed: bool = True) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        prompt_id: {
            "outputs": {"9": {"images": [{"filename": "vpipe_00001_.png", "type": "output", "subfolder": ""}]}},
            "status": {"completed": completed, "status_str": status_str},
        }
    }
    return mock


def test_wait_for_completion_success():
    client = ComfyClient("http://localhost:8188")
    pid = "pid-1"
    with patch.object(client._http, "get", return_value=_mock_history_response(pid, "success")):
        entry = client.wait_for_completion(pid, timeout=5)
    assert "outputs" in entry
    client.close()


def test_wait_for_completion_error_status():
    client = ComfyClient("http://localhost:8188")
    pid = "pid-err"
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        pid: {"status": {"completed": False, "status_str": "error", "messages": ["OOM"]}}
    }
    with patch.object(client._http, "get", return_value=mock):
        with pytest.raises(ComfyError, match="Generation failed"):
            client.wait_for_completion(pid, timeout=5)
    client.close()


def test_wait_for_completion_timeout():
    client = ComfyClient("http://localhost:8188")
    pid = "pid-slow"
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {}  # prompt not in history yet

    with patch.object(client._http, "get", return_value=mock):
        with patch("time.sleep"):  # don't actually sleep
            with pytest.raises(ComfyTimeoutError):
                client.wait_for_completion(pid, timeout=0)
    client.close()


# ── ComfyClient.download_outputs ─────────────────────────────────────────────

def test_download_outputs(tmp_path: Path):
    client = ComfyClient("http://localhost:8188")
    pid = "pid-dl"
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

    history_mock = MagicMock()
    history_mock.raise_for_status = MagicMock()
    history_mock.json.return_value = {
        pid: {
            "outputs": {
                "9": {"images": [{"filename": "vpipe_00001_.png", "type": "output", "subfolder": ""}]}
            }
        }
    }
    img_mock = MagicMock()
    img_mock.raise_for_status = MagicMock()
    img_mock.content = fake_png

    with patch.object(client._http, "get", side_effect=[history_mock, img_mock]):
        saved = client.download_outputs(pid, tmp_path)

    assert len(saved) == 1
    assert saved[0].name == "vpipe_00001_.png"
    assert saved[0].read_bytes() == fake_png
    client.close()
