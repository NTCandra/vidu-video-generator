# Character LoRA Training

## Overview

Each main character gets a dedicated LoRA trained on 20-30 reference images.  
This ensures >90% facial consistency across generated scenes.

## 1. Build reference image set

Use `workflows/txt2img_base.json` in ComfyUI to generate a character sheet:
- **20-30 images**, varied: angles (front, 3/4, profile), expressions, lighting, outfits
- Lock the art style with your style preset from `config/styles/default.yaml`
- Use the same seed + ControlNet openpose for pose variation while keeping face stable
- Manually curate — remove blurry, distorted, or inconsistent images

## 2. Caption each image

Name caption files `<image_name>.txt`. Format: `{trigger_word}, 1girl/1boy, <descriptive tags>`

Example for a character `example_char_v1`:
```
example_char_v1, 1girl, long black hair, amber eyes, cultivation robes, looking at viewer
```

Rules:
- Trigger word **first**, always
- Use descriptive tags, not artistic quality tags (no "masterpiece" etc. in training captions)
- Separate character tags from scene/bg tags with `BREAK` if training on complex scenes

## 3. Create character config

Copy `config/characters/example.yaml` → `config/characters/<char_id>.yaml` and fill in:
- `trigger_word` — must match caption prefix exactly
- `lora_path` — where the output .safetensors will be saved

## 4. Run training

```bash
uv run python scripts/train_character_lora.py \
    --config config/characters/<char_id>.yaml \
    --refs data/references/characters/<char_id>/ \
    --kohya-dir ~/kohya_ss \
    --base-model ~/ComfyUI/models/checkpoints/illustriousXL_v01.safetensors
```

**Expected GPU time:** ~30-60 minutes on 24 GB VRAM (1200 steps, batch 1).

## 5. Validate

Load `workflows/txt2img_lora.json` in ComfyUI and test with 10 prompts:
- Different poses and outfits
- Different backgrounds / lighting
- Emotional expressions: happy, sad, serious, surprised

Target: >90% facial consistency across all 10.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Face inconsistent | Add more front-facing refs; increase rank to 48 |
| Style bleeds into outputs | Reduce `lora_strength` to 0.65-0.75 |
| OOM during training | Set `cache_latents_to_disk: true`, reduce batch to 1 |
| Training loss not decreasing | Check caption format; verify trigger word is first |
