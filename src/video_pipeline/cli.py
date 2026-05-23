"""vpipe — Vietnamese anime video generation pipeline CLI."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="vpipe",
    help="Automated Vietnamese anime video pipeline. Run phases individually or end-to-end.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def scenes(
    story: str = typer.Option(..., "--story", "-s", help="Path to story .md file"),
    out: str = typer.Option("data/intermediate", "--out", "-o", help="Output path for scenes.json"),
) -> None:
    """Phase 5 — Break a story .md into structured scenes.json via LLM."""
    console.print("[yellow]scenes: not implemented yet[/yellow]")
    raise typer.Exit(code=1)


@app.command()
def images(
    scenes_path: str = typer.Option(..., "--scenes", help="Path to scenes.json"),
    workflow: str = typer.Option("txt2img_base", "--workflow", "-w", help="Workflow name (without .json)"),
    out: str = typer.Option("data/intermediate", "--out", "-o", help="Output directory for PNGs"),
) -> None:
    """Phase 2 — Generate images for each scene via ComfyUI API."""
    console.print("[yellow]images: not implemented yet[/yellow]")
    raise typer.Exit(code=1)


@app.command()
def voice(
    scenes_path: str = typer.Option(..., "--scenes", help="Path to scenes.json"),
    out: str = typer.Option("data/intermediate", "--out", "-o", help="Output directory for WAV files"),
) -> None:
    """Phase 4 — Synthesize Vietnamese narration audio for each scene."""
    console.print("[yellow]voice: not implemented yet[/yellow]")
    raise typer.Exit(code=1)


@app.command()
def animate(
    scenes_path: str = typer.Option(..., "--scenes", help="Path to scenes.json"),
    images_dir: str = typer.Option(..., "--images-dir", help="Directory of scene PNGs"),
    out: str = typer.Option("data/intermediate", "--out", "-o", help="Output directory for scene clips"),
) -> None:
    """Phase 6 — Animate scene images (Ken Burns / I2V / lip-sync)."""
    console.print("[yellow]animate: not implemented yet[/yellow]")
    raise typer.Exit(code=1)


@app.command()
def assemble(
    run_dir: str = typer.Option(..., "--run-dir", help="Intermediate run directory (contains scenes, images, audio, clips)"),
    out: str = typer.Option("data/output", "--out", "-o", help="Output path for final mp4"),
) -> None:
    """Phase 7 — Assemble clips + audio + subtitles + BGM into final mp4."""
    console.print("[yellow]assemble: not implemented yet[/yellow]")
    raise typer.Exit(code=1)


@app.command()
def run(
    story: str = typer.Option(..., "--story", "-s", help="Path to story .md file"),
    out: str = typer.Option("data/output", "--out", "-o", help="Output directory for final mp4"),
    from_phase: str = typer.Option("scenes", "--from", help="Resume from this phase: scenes|images|voice|animate|assemble"),
    review: bool = typer.Option(False, "--review", help="Generate report.html for human review before final assembly"),
) -> None:
    """Phase 9 — Run full pipeline end-to-end (phases 5 → 8) with checkpointing."""
    console.print("[yellow]run: not implemented yet[/yellow]")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
