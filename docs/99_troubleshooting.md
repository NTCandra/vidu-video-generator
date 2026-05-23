# Troubleshooting

## ComfyUI

**ComfyUI not responding**
```bash
curl http://localhost:8188/system_stats
```
If no response, restart ComfyUI. Check GPU memory: `nvidia-smi`.

**`vpipe images` times out**
- Increase `imagegen.timeout_sec` in `config/pipeline.yaml`
- Check ComfyUI is running: `COMFYUI_URL` in `.env`

**Images look wrong style**
- Verify the correct checkpoint is loaded in the workflow JSON
- Check `config/styles/default.yaml` positive/negative tags are being applied

## Ollama / LLM

**scene breakdown returns invalid JSON**
- The pipeline retries 3× with the validator error fed back to the LLM
- If still failing, try a larger model or switch to `anthropic` backend in `pipeline.yaml`
- Check Ollama is running: `ollama list`

**Ollama OOM**
- Qwen 2.5 32B Q4_K_M needs ~20 GB RAM. Ensure no other large models are loaded.
- Use `ollama stop <model>` to free memory

## TTS

**Diacritics mispronounced**
- Verify the reference transcript matches the audio exactly, including all tones
- Add a normalization entry to the text normalizer for specific words

**GPT-SoVITS API not responding**
- Check it's started: `curl http://localhost:9880`
- The API server must be started manually before running `vpipe voice`

## Assembly

**Subtitles missing diacritics**
- Ensure `Be Vietnam Pro` font is in `assets/fonts/` and path matches `pipeline.yaml`
- Check FFmpeg version supports the `drawtext` filter with UTF-8

**Audio out of sync**
- Check per-scene WAV duration matches `est_duration_sec` in scenes.json
- The assembly timeline uses narration duration as ground truth; adjust `est_duration_sec` in scenes manually if needed

## General

**`uv sync` fails**
- Ensure Python 3.11+ is active: `python --version`
- Try: `uv venv --python 3.11 && uv sync`

**Permission denied on scripts**
- `chmod +x scripts/setup_comfyui_nodes.sh`
