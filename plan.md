# AI Video Generation Pipeline — Implementation Plan

> **Purpose of this document:** This is a phased implementation plan for Claude Code to execute. Each phase has clearly scoped tasks, acceptance criteria, and a split between what Claude Code builds vs. what the human operator does. Phases are designed to be picked up one at a time.

---

## 1. Project Goal

Build a local-first, semi-to-fully-automated pipeline to produce **Vietnamese-language anime/stylized narrative videos** (≤10 min) for YouTube, targeting cultivation (tu tiên) / fantasy / romance genres with **consistent recurring characters**.

- **Hardware target:** 96GB RAM + 24GB VRAM (NVIDIA), Linux or Windows with WSL2.
- **Long-term output cadence:** 1 video / 2-3 days, mostly automated.
- **Quality bar:** "decent enough" — clear narrative flow, consistent character faces across scenes, natural Vietnamese narration, watchable motion.

This is **not** a fully autonomous YouTube farm. It is an opinionated pipeline that turns a written story into a finished video with minimal human intervention, where the human still owns creative direction.

---

## 2. Architecture

```
┌──────────────────┐
│   Story (.md)    │  Human-written or LLM-drafted
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Scene Breakdown  │  Local LLM → scenes.json
│   (LLM)          │  {narration, image_prompt, characters, mood, duration}
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌────────────────────┐
│   Image Gen      │◄─────┤ Character LoRAs    │
│  (ComfyUI API)   │      │ + IPAdapter refs   │
└────────┬─────────┘      └────────────────────┘
         │
         │  Static keyframes (PNG, one per scene)
         ▼
┌──────────────────┐      ┌────────────────────┐
│   Voice Gen      │◄─────┤  Voice profiles    │
│   (TTS)          │      │  (cloned samples)  │
└────────┬─────────┘      └────────────────────┘
         │
         ▼
┌──────────────────┐
│   Motion         │  Ken Burns (default), I2V (key moments),
│  (FFmpeg + I2V)  │  LivePortrait (talking scenes)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Assembly       │  MoviePy: video + voice + BGM + subtitles
│  (MoviePy)       │  → final mp4 (1080p, H.264)
└────────┬─────────┘
         │
         ▼
     output.mp4
```

Key principle: **don't full-text-to-video.** Generate high-quality static keyframes and animate selectively. For a 10-min video this is ~30-60× cheaper in compute than naive T2V.

---

## 3. Tech Stack

| Component | Primary choice | Alternative / fallback |
|-----------|----------------|------------------------|
| Orchestrator | Python 3.11+, Typer CLI | n8n / Airflow (later) |
| Dependency manager | `uv` (pyproject.toml + uv.lock) | poetry, pip-tools |
| LLM (scene breakdown) | Qwen 2.5 32B Instruct (Q4_K_M, via Ollama) | Anthropic API (premium runs) |
| Image gen | ComfyUI + Illustrious XL | NoobAI XL, Animagine XL 4, Pony V6 |
| Character consistency | Trained LoRA per main character (kohya_ss); IPAdapter/PuLID for side chars | Reference-only ControlNet |
| Video (I2V, selective) | Wan 2.2 I2V | LTX-Video, CogVideoX |
| Lip-sync | LivePortrait | Hallo3 |
| TTS (Vietnamese) | F5-TTS or GPT-SoVITS | XTTS-v2 |
| ASR (for subtitles) | faster-whisper large-v3 | — |
| Assembly | MoviePy + FFmpeg | — |
| Configs | YAML, validated with Pydantic | — |

> ⚠ **Verify before Phase 1.** Local AI tooling moves fast. Check Civitai, Hugging Face, and r/StableDiffusion for current best-in-class anime SDXL checkpoint and video model before committing. Update this table in a PR if a clearly better option exists.

---

## 4. Directory Structure

```
ai-video-pipeline/
├── README.md
├── plan.md                          # this file
├── .gitignore
├── .env.example
├── pyproject.toml
├── uv.lock
├── config/
│   ├── pipeline.yaml                # central config
│   ├── characters/                  # per-character configs
│   │   └── example.yaml
│   └── styles/                      # visual style presets
│       └── default.yaml
├── src/
│   └── video_pipeline/
│       ├── __init__.py
│       ├── llm/
│       │   ├── client.py            # unified LLM interface (Ollama / Anthropic)
│       │   └── scene_breakdown.py
│       ├── imagegen/
│       │   ├── comfy_client.py      # ComfyUI HTTP API wrapper
│       │   └── batch.py
│       ├── tts/
│       │   ├── client.py
│       │   └── voice_profiles.py
│       ├── motion/
│       │   ├── ken_burns.py
│       │   ├── i2v.py
│       │   └── lip_sync.py
│       ├── assembly/
│       │   ├── timeline.py
│       │   └── render.py
│       └── cli.py                   # `vpipe` command entry
├── workflows/                       # ComfyUI workflow JSONs (versioned)
│   ├── txt2img_base.json
│   ├── txt2img_lora.json
│   ├── img2img_refine.json
│   └── i2v_wan22.json
├── scripts/
│   ├── setup_comfyui_nodes.sh
│   ├── download_models.py
│   └── train_character_lora.py
├── data/                            # gitignored
│   ├── stories/                     # input scripts (.md)
│   ├── references/
│   │   ├── characters/              # ref images for LoRA training
│   │   └── voices/                  # TTS reference audio
│   ├── intermediate/                # per-run artifacts
│   │   └── <video_id>/
│   └── output/                      # final videos + manifests
├── docs/
│   ├── 00_quickstart.md
│   ├── 01_setup_comfyui.md
│   ├── 02_train_lora.md
│   ├── 03_first_video.md
│   ├── 04_voice_cloning.md
│   └── 99_troubleshooting.md
└── tests/
    └── ...
```

---

## 5. Phased Implementation

Each phase: **Goal**, **Claude Code tasks**, **Human tasks**, **Acceptance criteria**.

### Phase 0 — Repo skeleton (Claude Code, ~30 min)

**Goal:** Bootstrap repo with structure, tooling, baseline configs.

**Claude Code tasks:**
- Create the full directory tree per Section 4.
- Write `pyproject.toml` with deps: `requests`, `httpx`, `pydantic>=2`, `pyyaml`, `moviepy`, `faster-whisper`, `ollama`, `huggingface_hub`, `pillow`, `numpy`, `typer`, `rich`, `python-dotenv`. Dev deps: `ruff`, `mypy`, `pytest`.
- Write `.gitignore` excluding: `data/`, `models/`, `*.safetensors`, `*.ckpt`, `*.pt`, `*.gguf`, `.env`, `__pycache__/`, `.venv/`, `*.mp4`, `*.wav`, `*.png` (except `docs/assets/`).
- Write `.env.example` with: `COMFYUI_URL` (default `http://127.0.0.1:8188`), `OLLAMA_URL` (default `http://127.0.0.1:11434`), `ANTHROPIC_API_KEY` (optional).
- Write `config/pipeline.yaml` skeleton with sections: `llm`, `imagegen`, `tts`, `motion`, `assembly`. Document every key with comments.
- Write `config/characters/example.yaml` showing schema: `name`, `trigger_word`, `lora_path`, `default_prompt_tags`, `negative_tags`, `voice_profile`.
- Write `config/styles/default.yaml`: positive/negative style tag presets, sampler defaults.
- Write `README.md`: project description, hardware requirements, pointer to `docs/00_quickstart.md`.
- Initialize Typer CLI in `src/video_pipeline/cli.py` with placeholder commands: `scenes`, `images`, `voice`, `animate`, `assemble`, `run`. Each prints "not implemented" for now.
- Register console script `vpipe = video_pipeline.cli:app` in `pyproject.toml`.
- Configure ruff + mypy in `pyproject.toml`.

**Human tasks:** `git init`, `gh repo create --private <name>`, first commit & push.

**Acceptance:** Repo clones cleanly. `uv sync` installs without errors. `uv run vpipe --help` lists all six commands.

---

### Phase 1 — ComfyUI environment & first image (mostly human, Claude Code assists)

**Goal:** ComfyUI ready with the anime base model + key custom nodes. Operator can generate a stylized character image manually in the ComfyUI UI.

**Claude Code tasks:**
- Write `scripts/setup_comfyui_nodes.sh` that installs (via `git clone` into `ComfyUI/custom_nodes/`):
  - ComfyUI-Manager
  - ComfyUI_IPAdapter_plus
  - ComfyUI-Impact-Pack
  - ComfyUI-Custom-Scripts
  - ComfyUI-Easy-Use
  - ComfyUI-PuLID (or successor)
  - ComfyUI-VideoHelperSuite (for later phases)
  Script must be idempotent (skip if already cloned).
- Write `scripts/download_models.py` using `huggingface_hub.snapshot_download`:
  - Illustrious XL base checkpoint → `ComfyUI/models/checkpoints/`
  - SDXL VAE (fp16) → `ComfyUI/models/vae/`
  - IPAdapter SDXL models + CLIPVision → respective dirs
  - Print file hashes after download for verification.
  - Take a `--profile` flag: `phase1` downloads only what Phase 1 needs.
- Write `workflows/txt2img_base.json`: a clean ComfyUI workflow with:
  - Checkpoint loader, CLIP text encoders (pos/neg), KSampler, VAE decode, SaveImage.
  - Sensible defaults: 1024×1024, 28 steps, DPM++ 2M Karras, CFG 6-7.
- Write `docs/01_setup_comfyui.md` with screenshots placeholders and step-by-step (install nodes → restart ComfyUI → load workflow → generate).

**Human tasks:**
- Run setup script and model download.
- Open ComfyUI UI, load `txt2img_base.json`, generate first images.
- Iterate prompts until happy with the visual baseline; save 2-3 example prompts as comments in `config/styles/default.yaml`.

**Acceptance:** Operator produces a stylized portrait in ComfyUI UI in <30s per image; visual style matches target (anime / cultivation aesthetic).

---

### Phase 2 — Programmatic image generation via ComfyUI API (Claude Code)

**Goal:** Drive ComfyUI from Python.

**Claude Code tasks:**
- Implement `src/video_pipeline/imagegen/comfy_client.py`:
  - `submit_workflow(workflow_dict, params) -> prompt_id` (POST `/prompt`).
  - `wait_for_completion(prompt_id, timeout=300) -> history_entry` (poll `/history/{id}`).
  - `download_outputs(prompt_id) -> list[Path]` (GET `/view` for each image).
  - `inject_params(workflow_dict, mapping)` — safe template substitution. Mapping resolves `{{positive_prompt}}`, `{{negative_prompt}}`, `{{seed}}`, `{{lora_name}}`, etc., to node fields. Document which node IDs in each workflow are "parameterized" — keep a small registry.
  - Connection errors → typed exceptions with helpful messages.
- Implement `src/video_pipeline/imagegen/batch.py`:
  - `generate_batch(scenes, workflow_path, output_dir) -> dict[scene_id, Path]`.
  - Serialize requests (ComfyUI processes one at a time anyway); show rich progress bar.
- Implement `vpipe images --scenes <path> --workflow <name> --out <dir>` CLI.
- Unit tests with mocked HTTP responses.

**Acceptance:** `vpipe images` reads a small `scenes.json` (5 scenes) and produces 5 PNGs in `data/intermediate/<run>/images/`.

---

### Phase 3 — Character LoRA training (Claude Code writes harness; human supervises)

**Goal:** Train a reusable LoRA for one main character. Process must be repeatable for future characters.

**Claude Code tasks:**
- Write `scripts/train_character_lora.py` wrapping `kohya_ss sd-scripts`:
  - Input: directory of reference images + a per-character YAML (trigger word, class token, training params overrides).
  - Output: `models/loras/characters/<name>.safetensors`.
  - Sensible SDXL defaults: rank 32, alpha 16, ~1200 steps, AdamW8bit, lr 1e-4 (unet) / 5e-5 (text encoder), batch 1-2, mixed precision fp16, network dropout 0.1, captioning style "tag-based with trigger word first".
  - Auto-resize/crop refs to 1024-bucket sizes.
  - Save training config snapshot next to output `.safetensors`.
- Write `docs/02_train_lora.md` covering:
  - How to generate a character sheet (20-30 angles/expressions) using Phase 1 workflow with a locked seed + ControlNet poses.
  - Captioning conventions (`{trigger_word}, 1girl/1boy, <descriptive tags>`).
  - Expected GPU time on 24GB (~30-60 min).
  - Validation steps: test prompts in `txt2img_lora.json`, eyeball facial consistency.
- Write `workflows/txt2img_lora.json`: extends base workflow with `LoraLoader` node.

**Human tasks:**
- For the first character: build a 20-30 image reference set (use Phase 1 to generate, manually curate).
- Run training.
- Validate with 10 test prompts in different poses/outfits/lighting.

**Acceptance:** LoRA produces the character with subjectively >90% facial consistency across 10 varied test prompts.

---

### Phase 4 — Vietnamese TTS (Claude Code + human voice samples)

**Goal:** Convert narration text → natural Vietnamese audio with cloned/consistent voice(s).

**Claude Code tasks:**
- Implement `src/video_pipeline/tts/client.py` with a `TTSBackend` protocol and concrete implementations:
  - `F5TTSBackend` (preferred, via official lib or subprocess).
  - `GPTSoVITSBackend` (subprocess to its API server).
  - `XTTSBackend` (zero-shot fallback, via `coqui-tts`).
- Backend selection via `config/pipeline.yaml`.
- `VoiceProfile` model: `id`, `display_name`, `backend`, `reference_audio_path`, `reference_text` (transcript of reference clip), `language` (default `vi`).
- `synthesize(text, voice_profile) -> Path` returns 22kHz mono WAV.
- Loudness normalization to -16 LUFS via `pyloudnorm` or ffmpeg `loudnorm`.
- `vpipe voice --scenes <path> --out <dir>` produces per-scene WAV files using the voice profile referenced in each scene.
- Write `docs/04_voice_cloning.md`: how to record references (quiet room, 3-30s, 22kHz mono, transcribe accurately), how to add new profiles.

**Human tasks:**
- Record or source 2-3 voice samples: narrator + 1-2 main characters. Place in `data/references/voices/`.
- Fill in `config/characters/<name>.yaml` with `voice_profile` references.
- Listen/iterate.

**Acceptance:** A 5-paragraph Vietnamese script produces clean, natural-sounding audio per voice profile in <2 min total; diacritics pronounced correctly.

---

### Phase 5 — Story → scenes breakdown (Claude Code)

**Goal:** Local LLM converts a story (.md) into structured `scenes.json`.

**Claude Code tasks:**
- Implement `src/video_pipeline/llm/client.py`:
  - `LLMBackend` protocol: `generate_structured(system, user, schema) -> dict`.
  - `OllamaBackend` (default, local, model from config).
  - `AnthropicBackend` (uses `ANTHROPIC_API_KEY`, for premium runs).
- Implement `src/video_pipeline/llm/scene_breakdown.py`:
  - Input: `story.md`, character roster (loaded from `config/characters/`), style preset (loaded from `config/styles/`).
  - System prompt enforces output JSON schema:
    ```
    {
      "title": str,
      "scenes": [
        {
          "id": str,                    # e.g., "s001"
          "narration_vi": str,          # what the narrator says (Vietnamese)
          "image_prompt_en": str,       # English prompt for image model
          "characters": [str],          # character IDs present
          "talking_character": str?,    # for lip-sync scenes
          "mood": str,                  # for music/motion selection
          "motion": "ken_burns" | "i2v" | "lipsync",
          "est_duration_sec": float
        }
      ]
    }
    ```
  - Validate with Pydantic; retry up to 3× on schema failure with the validator error fed back to the LLM.
  - Image prompts MUST reference character trigger words from the loaded character configs.
- `vpipe scenes --story <path> --out <path>` CLI.
- Include 1-2 few-shot examples in the system prompt to lock register (kể chuyện 3rd-person, ~1-3 sentences per scene).

**Acceptance:** A 1500-word Vietnamese story produces 30-50 well-formed scenes; all character trigger words appear correctly; narration reads naturally.

---

### Phase 6 — Motion: Ken Burns + selective I2V (Claude Code)

**Goal:** Animate static keyframes. Ken Burns by default, I2V for scenes marked `motion: i2v`.

**Claude Code tasks:**
- Implement `src/video_pipeline/motion/ken_burns.py`:
  - Given image + duration + mood → mp4 with subtle zoom/pan (FFmpeg `zoompan` filter or moviepy).
  - Mood → motion preset mapping (calm = slow zoom out; tense = slow zoom in; action = pan).
- Implement `src/video_pipeline/motion/i2v.py`:
  - Wraps Wan 2.2 via ComfyUI workflow `workflows/i2v_wan22.json`.
  - Input: image path + brief motion prompt → 3-5s mp4.
  - Falls back to Ken Burns on failure (logged warning).
- Add to `download_models.py` a `phase6` profile to fetch Wan 2.2 weights.
- `vpipe animate --scenes <path> --images-dir <path> --out <dir>` produces per-scene mp4 clips.

**Acceptance:** A mixed set (8 Ken Burns + 2 I2V) processes in <10 min on the target hardware.

---

### Phase 7 — Assembly: timeline, audio, subtitles, BGM (Claude Code)

**Goal:** Produce a final YouTube-ready mp4.

**Claude Code tasks:**
- Implement `src/video_pipeline/assembly/timeline.py`:
  - Concatenate per-scene clips with configurable crossfades.
  - Mux per-scene narration onto matching scene window.
  - Background music: load from `data/references/bgm/`, duck under narration (-12 dB during speech), fade in/out.
- Subtitle generation:
  - Run faster-whisper large-v3 on the concatenated narration WAV → SRT.
  - Vietnamese language hint.
  - Burn into video via FFmpeg with a Vietnamese-diacritic-safe font (default: Be Vietnam Pro), styled (semi-transparent dark background, white text, bottom-center).
- Final render: 1080p (1920×1080), H.264 yuv420p, AAC audio 192k, CRF 18-20.
- Write `data/output/<video_id>.mp4` + `<video_id>.json` manifest containing: story path, scenes hash, model versions, seeds, total duration, render time.
- `vpipe assemble --run-dir <path> --out <path>` CLI.

**Acceptance:** End-to-end on a sample 1500-word story produces a watchable 3-5 min video with synced audio, readable subtitles, and tasteful BGM ducking. Plays correctly on YouTube preview.

---

### Phase 8 — Lip-sync for talking scenes (Claude Code)

**Goal:** When `motion: lipsync`, drive the talking character's face with LivePortrait against the scene's narration audio.

**Claude Code tasks:**
- Implement `src/video_pipeline/motion/lip_sync.py` wrapping LivePortrait (subprocess or ComfyUI workflow).
- Use the character image generated for that scene (must contain the `talking_character` from scenes.json) as the driving face source.
- Length-match output to narration audio.

**Acceptance:** Lip-sync looks credible at conversational pace; no major artifacts on side-profile shots.

---

### Phase 9 — Orchestrator + quality gates (Claude Code)

**Goal:** Single command `vpipe run --story <path>` executes phases 5 → 8 end-to-end with checkpointing.

**Claude Code tasks:**
- `vpipe run` writes intermediate artifacts to `data/intermediate/<run_id>/` so any phase can resume.
- `--from <phase>` flag to skip earlier phases if their outputs exist.
- Quality gates:
  - Per-image CLIP score vs. prompt. If below threshold, regen with a new seed (max 3 retries).
  - Per-scene audio duration sanity check (narration ≤ 1.5× scene duration).
- Cost/time logging per run (LLM tokens, GPU seconds, total wall time).
- Optional `--review` flag generates `report.html` with thumbnails + transcripts for human review before final assembly.

**Acceptance:** 80%+ of runs produce a finalized video without manual intervention; failed runs leave clear artifacts for debugging.

---

### Phase 10 — Productionization (backlog, do not implement yet)

Track as future work, do not implement during initial buildout:
- n8n or Airflow for scheduled batch runs.
- YouTube Data API direct upload (`scripts/upload_youtube.py`) with thumbnail/title/description from the manifest.
- Analytics ingestion (which thumbnails/titles perform best) → feedback loop into Phase 5 prompts.
- Multi-channel branch (different style presets, voice profiles, branding per channel).
- Web dashboard (Streamlit / Gradio) for non-CLI review and approval.

---

## 6. Conventions

- **Code style:** ruff (lint + format), mypy on `src/` (strict per-module, loosen for third-party glue).
- **Configs over code:** YAML + Pydantic schemas. Never hardcode model paths, prompts, or magic numbers in Python — pull from config.
- **Secrets:** `.env` only, never committed. Use `python-dotenv`. `.env.example` documents every required key.
- **Large binaries:** never in git. `data/` and `models/` are gitignored. Distribute via Hugging Face Hub (private repo) or local NAS.
- **Reproducibility:** every render writes a manifest with seeds, model hashes, workflow JSON snapshots. A finished video must be re-derivable from its manifest + story file.
- **Logging:** `rich` for human-readable; structured JSON logs available via `LOG_FORMAT=json` env var.
- **Errors:** raise typed exceptions defined per module. CLI exits non-zero on failure with a clear message.
- **Tests:** unit tests for pure logic (prompt templating, schema validation, timeline math). Skip integration tests against ComfyUI / Ollama in CI; provide a `make test-integration` target that runs locally.
- **ComfyUI workflows are source code:** version them, never edit silently. When changing a workflow, bump a version field in its filename or metadata.

---

## 7. Vietnamese-Specific Notes

- **TTS reference samples:** Record in a quiet room, 22kHz mono WAV, 3-30s, with an accurate transcript. Northern Vietnamese accent by default; can branch per target audience.
- **LLM prompting:** System prompt explicitly states `"viết tiếng Việt tự nhiên, kể chuyện ngôi thứ ba"` and provides 1-2 few-shot examples. Few-shot examples should differentiate narration register from character dialogue.
- **Image prompts to image models stay in English** — SDXL/Illustrious training data is English-dominant. Only narration is Vietnamese. The LLM does the translation as part of scene breakdown.
- **Subtitle font:** Be Vietnam Pro (preferred) or Noto Sans Vietnamese — both render all diacritics correctly. Ship the chosen `.ttf` in `assets/fonts/` (check the license before committing).
- **Numbers, dates, abbreviations** in narration should be spelled out in Vietnamese for TTS (`"15"` → `"mười lăm"`, `"TP.HCM"` → `"Thành phố Hồ Chí Minh"`). Add a normalization pass before TTS in Phase 4.
- **ASR for subtitles:** faster-whisper large-v3 with `language="vi"`. Verify on first run — Whisper occasionally drops diacritics; have a post-process pass that re-aligns subtitle text against the LLM's original narration where possible.

---

## 8. Recommended First-Run Roadmap

| Week | Phases | Deliverable |
|------|--------|-------------|
| 1 | Phase 0 → Phase 1 → Phase 2 | Programmatic image generation works end-to-end |
| 2 | Phase 3 → Phase 4 | One consistent main character (LoRA) + 2 voice profiles ready |
| 3 | Phase 5 → Phase 6 (Ken Burns only) → Phase 7 | First end-to-end pilot video, 3-5 min, no lip-sync |
| 4 | Phase 8 → Phase 9 | Lip-sync working, orchestrator with quality gates |
| Month 2+ | Phase 10 | Productionization |

After each phase, **the operator should produce one concrete artifact** (a generated image, a trained LoRA, a voice sample, a pilot video) and review it before moving on. The plan optimizes for early concrete output, not for "build everything first."

---

## 9. Open Questions to Resolve Before Phase 5

These need a human decision; Claude Code should NOT guess:

1. **First series concept** — adapt one of the existing novels (e.g., *Bách Sắc Thần Phong*, *Tu Tiên Giờ Hành Chính*), or start a fresh storyline?
2. **Character roster for series 1** — names, archetypes, visual descriptors. Need 2-3 main characters minimum.
3. **Visual style anchor** — which artist/anime style is the target reference? (e.g., "modern manhua", "soft cel-shaded", "ink-wash inspired"). This shapes Phase 1's style preset.
4. **Narrator voice** — clone the operator's voice, use an existing voice actor sample (with permission/license), or use a synthetic preset?
5. **Channel branding** — how does this fit `itfromthestars.com`? Cross-promotion strategy?

Resolving these unlocks Phase 5 with the right defaults baked in.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Model ecosystem shifts mid-build (e.g., better anime model drops) | Configs decouple model choice from code; document upgrade path |
| 24GB VRAM not enough for a future model | Plan supports CPU offload via `accelerate`; can downgrade to SD 1.5-based stack if needed |
| Vietnamese TTS quality insufficient | Multiple backends supported; can swap without changing pipeline |
| Character drift across long videos | Quality gate in Phase 9 with CLIP / face-embedding similarity check |
| YouTube ToS on AI content | Pipeline produces fully disclosed AI-assisted content; comply with YouTube's labeling requirements at upload time |
| Compute time per video too long for cadence target | Profile in Phase 7; Ken Burns–dominant default keeps per-video render under ~2 hours |

---

*End of plan.*
