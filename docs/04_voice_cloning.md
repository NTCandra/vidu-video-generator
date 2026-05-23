# Voice Cloning for Vietnamese TTS

## Recording reference audio

For best results with GPT-SoVITS or F5-TTS voice cloning:

- **Environment:** quiet room, no echo, no background noise
- **Length:** 3-30 seconds of clean speech
- **Format:** 22 kHz mono WAV (record at higher quality and downsample if needed)
- **Content:** natural Vietnamese sentences; avoid reading lists or fillers
- **Diacritics:** speak clearly and enunciate all tones correctly
- **Accent:** Northern Vietnamese by default; record Southern if targeting that audience

```bash
# Convert to 22kHz mono WAV with ffmpeg
ffmpeg -i input.mp3 -ar 22050 -ac 1 data/references/voices/narrator.wav
```

## Adding a voice profile

1. Place WAV in `data/references/voices/<profile_id>.wav`
2. Write an accurate transcript — **exact** text, including all diacritics
3. Add a profile to `config/characters/<char_id>.yaml`:

```yaml
voice_profile: "narrator"
```

Voice profiles are defined by convention: `<profile_id>` maps to:
- Audio: `data/references/voices/<profile_id>.wav`
- Transcript: `data/references/voices/<profile_id>.txt`

## Testing a voice profile

```bash
uv run vpipe voice --scenes data/stories/test_scenes.json --out data/intermediate/test_voice/
```

Listen to the output WAVs. Check:
- All diacritics pronounced correctly (especially hỏi/ngã/nặng tones)
- Natural rhythm and pacing
- No artifacts at sentence boundaries

## Text normalization

Numbers, dates, and abbreviations must be spelled out for TTS:
- `"15"` → `"mười lăm"`
- `"TP.HCM"` → `"Thành phố Hồ Chí Minh"`
- `"km"` → `"ki-lô-mét"`

The pipeline (Phase 4) includes a normalization pass before TTS synthesis.
