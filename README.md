# What Happens When You Press Send?

A finished 71.5-second cartoon explainer with ElevenLabs narration, timed subtitles, and background music.

The finished `final.mp4` is approximately 71.5 seconds, with eight George narration clips using ElevenLabs Flash v2.5, synchronized full subtitles, and the user's licensed “Science Lab” track by 2BStudio mixed quietly underneath. The original 104-second silent preview remains available. `final-hd.mp4` is a new 1920×1080 / 30 fps render from the original artwork, with text and animation overlays drawn at the full output resolution. Original narration, scenes.json, and artwork are unchanged; final scene durations are derived from the recorded speech.

`final.srt` contains the 31 timed subtitle phrases. `subtitles.json` contains the render timeline and exact phrase timings. `audio/` contains reusable MP3 clips and alignment data. `music/science-lab.webm` is the chosen background track from https://www.youtube.com/watch?v=6w6Cq3ZNUWk (user confirmed an existing license).

To reproduce the completed 720p edit without generating speech again:

```powershell
.\.venv\Scripts\python.exe prepare_subtitles.py
.\.venv\Scripts\python.exe render_video.py --scene-audio-dir audio --music music/science-lab.webm --subtitles subtitles.json --output final.mp4
```

To render directly from the original artwork at 1920×1080 and 30 fps, with sharper text and smoother animation:

```powershell
.\.venv\Scripts\python.exe render_video.py --scene-audio-dir audio --music music/science-lab.webm --subtitles subtitles.json --width 1920 --height 1080 --fps 30 --crf 18 --preset medium --output final-hd.mp4
```

On this Windows machine, FFmpeg and ffprobe are installed in `%LOCALAPPDATA%\Programs\MessageExplainer\ffmpeg\package` and added to the user PATH. Open a new terminal after installation so it picks up the updated PATH.

## Files

- `assets/`: original generated illustrations used by the edit.
- `scenes.json`: narration, rough durations, and scene captions. Adjust durations after the narrator audio is available.
- `narration.txt`: clean text to send to ElevenLabs.
- `render_video.py`: reproducible animation and video render using Python, Pillow, and FFmpeg.
- `generate_narration.py`: ElevenLabs API narration, one clip per scene for accurate sync.
- `preview-silent.mp4`: a captioned silent animatic for reviewing the images and pacing.

## Animation

Wi-Fi marks pulse, an envelope travels over the linked neighborhood and router path, packet envelopes gently bob, and each illustration has a slow camera drift. These motions repeat within their scenes, while the full video plays once.

## Add the voice and music

On Windows, open PowerShell in this folder. Python and FFmpeg (including ffprobe) must be installed and available on PATH. To install the Python packages:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Captions use Windows Segoe UI, with Arial as a fallback, at the intended text sizes.

Enter your ElevenLabs key privately in the local `.env` beside `generate_narration.py`, using the `ELEVENLABS_API_KEY` entry. The script loads that file regardless of the working directory; an existing process environment value takes precedence. Never paste the key into chat or command arguments. `.env` is excluded from Git and Git archives.

The script uses ElevenLabs Flash v2.5 and the George voice ID from the ElevenLabs API example by default. It checks the account's reported balance and resumes from any existing scene clips. Previewing does not contact ElevenLabs or generate speech:

```powershell
.\.venv\Scripts\python.exe generate_narration.py
```

Only after saving the key and confirming you want speech generated, run:

```powershell
.\.venv\Scripts\python.exe generate_narration.py --generate
.\.venv\Scripts\python.exe render_video.py --scene-audio-dir audio --output final.mp4
```

To share a ZIP, use this packaging command, which excludes `.env`, local environments, caches, partial downloads, temporary files, and nested ZIPs. Generic folder compression does not honor Git exclusions.

```powershell
.\.venv\Scripts\python.exe package_project.py
```

To change the background music, render with `--music path/to/music`. It is mixed quietly beneath the voice with a gentle fade at the beginning and end.

Each scene is automatically lengthened if its voice clip needs more time. The default 104-second timing is an estimate pending narration. Keep the ElevenLabs attribution required by your free plan in the description when sharing the finished noncommercial video.

## Factual basis

- Cloudflare, [How does the Internet work?](https://www.cloudflare.com/learning/network-layer/how-does-the-internet-work/)
- Cloudflare, [What is a router?](https://www.cloudflare.com/learning/network-layer/what-is-a-router/)
- IETF, [RFC 9293, TCP](https://www.rfc-editor.org/rfc/rfc9293)

This video depicts one typical chat-app flow. A service's delivery, encryption, and offline behavior can differ.
