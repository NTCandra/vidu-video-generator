"""Basic smoke tests for the CLI scaffold."""

from typer.testing import CliRunner

from video_pipeline.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("scenes", "images", "voice", "animate", "assemble", "run"):
        assert cmd in result.output


def test_scenes_not_implemented():
    result = runner.invoke(app, ["scenes", "--story", "fake.md"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_images_missing_scenes_file():
    result = runner.invoke(app, ["images", "--scenes", "nonexistent.json"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_voice_not_implemented():
    result = runner.invoke(app, ["voice", "--scenes", "fake.json"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_run_not_implemented():
    result = runner.invoke(app, ["run", "--story", "fake.md"])
    assert result.exit_code == 1
    assert "not implemented" in result.output
