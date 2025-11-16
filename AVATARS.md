# Avatar Configurations

This document tracks the reference video, audio, and text configurations for different avatars.

## Alex

**Description**: English-speaking avatar with clear English voice

**Reference Video**:
```
/code/data/temp/20251115031020305.mp4
```
Windows path: `D:/duix_avatar_data/face2face/temp/20251115031020305.mp4`
- Resolution: 1280x720 (720p HD)
- Duration: 11.1s

**Reference Audio**:
```
/code/data/origin_audio/format_denoise_20251115135836064.wav
```
Windows path: `D:/duix_avatar_data/voice/data/origin_audio/format_denoise_20251115135836064.wav`

**Reference Text**:
```
So they took it fun and the snowy days, and then it's got a big Christmas, and I'm going to have a Santa Claus. And then I'm going to have a wonderful day on spring, which is a check with what's my present, and then it'll be summer so I can roll, roll, roll your boat, and then fall, which is...
```

**Usage Example**:
```bash
# Generate video with Alex avatar
python scripts/generate_from_text.py my_script.txt \
  /code/data/temp/20251115031020305.mp4 \
  /code/data/origin_audio/format_denoise_20251115135836064.wav \
  "So they took it fun and the snowy days, and then it's got a big Christmas, and I'm going to have a Santa Claus. And then I'm going to have a wonderful day on spring, which is a check with what's my present, and then it'll be summer so I can roll, roll, roll your boat, and then fall, which is..."
```

**Generated Videos**:
- Deep Dive Trading (2025-11-15): `D:/duix_avatar_data/face2face/temp/39fa24ea-d25c-48bc-a47f-f0be1f90c602-r.mp4`
  - Duration: 79 seconds
  - Resolution: 3840x2160 (4K)
  - With subtitles: `D:/duix_avatar_data/face2face/temp/39fa24ea-d25c-48bc-a47f-f0be1f90c602-r_subtitled.mp4`

---

## Alex2

**Description**: English-speaking avatar with mixed Chinese-English voice

**Reference Video**:
```
/code/data/temp/20251115031020305.mp4
```
Windows path: `D:/duix_avatar_data/face2face/temp/20251115031020305.mp4`
- Resolution: 1280x720 (720p HD)
- Duration: 11.1s

**Reference Audio**:
```
/code/data/origin_audio/format_denoise_20251114215242697.wav
```
Windows path: `D:/duix_avatar_data/voice/data/origin_audio/format_denoise_20251114215242697.wav`

**Reference Text**:
```
这是我吗？嗯，of course， of course，我而我好想very fun。 by you妹妹哦，好好裤子trust出嗯中午。
```

**Usage Example**:
```bash
# Generate video with Alex2 avatar
python scripts/generate_from_text.py my_script.txt \
  /code/data/temp/20251115031020305.mp4 \
  /code/data/origin_audio/format_denoise_20251114215242697.wav \
  "这是我吗？嗯，of course， of course，我而我好想very fun。 by you妹妹哦，好好裤子trust出嗯中午。"
```

**Generated Videos**:
- (No videos generated yet)

---

## Evan

**Description**: Chinese-speaking avatar

**Reference Video**:
```
/code/data/temp/20251115000845014.mp4
```
Windows path: `D:/duix_avatar_data/face2face/temp/20251115000845014.mp4`

**Reference Audio**:
```
/code/data/origin_audio/format_denoise_20251115000845014.wav
```
Windows path: `D:/duix_avatar_data/voice/data/origin_audio/format_denoise_20251115000845014.wav`

**Reference Text**:
```
Dear Coach George, thank you for teaching me how to snowboard and encouraging me to go on harder. I really appreciate you teaching and guiding me to where I am now.
```

**Usage Example**:
```bash
# Generate video with Evan avatar
python scripts/generate_from_text.py my_script.txt \
  /code/data/temp/20251115000845014.mp4 \
  /code/data/origin_audio/format_denoise_20251115000845014.wav \
  "天空中滚，我睡觉了，老屋火车吃锅。哎呦，嗯你大逼你丑啊。"
```

**Generated Videos**:
- (No videos generated yet)

---

## Template for New Avatars

When adding a new avatar, copy this template:

```markdown
## [Avatar Name]

**Description**: [Brief description]

**Reference Video**:
```
[Container path]
```
Windows path: `[Windows path]`

**Reference Audio**:
```
[Container path]
```
Windows path: `[Windows path]`

**Reference Text**:
```
[Text transcription from reference audio]
```

**Usage Example**:
```bash
python scripts/generate_from_text.py my_script.txt \
  [video_path] \
  [audio_path] \
  "[reference_text]"
```

**Generated Videos**:
- [Description] ([Date]): `[Path]`
```
