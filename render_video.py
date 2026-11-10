"""Render the editable explainer animatic, optionally adding narration/music.

Usage: python render_video.py [--narration narration.mp3] [--music music.mp3]
Requires Pillow and FFmpeg. All timings and captions live in scenes.json.
"""

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1280, 720, 15
OUTPUT_W, OUTPUT_H, SCALE = W, H, 1.0
CRF, PRESET = 22, "veryfast"
BLUE = (31, 98, 226)
INK = (11, 38, 65)
CREAM = (255, 247, 232)


@lru_cache(maxsize=12)
def font(size):
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = [windows_fonts / "segoeui.ttf", windows_fonts / "arial.ttf",
                  Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), round(size * SCALE))
        except OSError:
            continue
    return ImageFont.load_default(size=round(size * SCALE))


class CanvasDraw:
    """Draw in the original 1280x720 design coordinates at output resolution."""

    def __init__(self, image):
        self.draw = ImageDraw.Draw(image)

    @staticmethod
    def coordinates(values):
        return tuple(round(value * SCALE) for value in values)

    def rectangle(self, xy, **kwargs):
        return self.draw.rectangle(self.coordinates(xy), **kwargs)

    def rounded_rectangle(self, xy, radius=0, width=1, **kwargs):
        return self.draw.rounded_rectangle(self.coordinates(xy), radius=round(radius * SCALE),
                                           width=max(1, round(width * SCALE)), **kwargs)

    def line(self, xy, width=1, **kwargs):
        return self.draw.line(self.coordinates(xy), width=max(1, round(width * SCALE)), **kwargs)

    def arc(self, xy, start, end, width=1, **kwargs):
        return self.draw.arc(self.coordinates(xy), start, end,
                             width=max(1, round(width * SCALE)), **kwargs)

    def text(self, xy, text, **kwargs):
        return self.draw.text(self.coordinates(xy), text, **kwargs)

    def textbbox(self, xy, text, **kwargs):
        return tuple(value / SCALE for value in
                     self.draw.textbbox(self.coordinates(xy), text, **kwargs))


def envelope(draw, x, y, width=94, color=BLUE, body=CREAM):
    height = int(width * 0.63)
    x, y = int(x), int(y)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=10, fill=body, outline=color, width=4)
    draw.line((x + 5, y + 7, x + width // 2, y + height // 2, x + width - 5, y + 7), fill=color, width=3)
    return width, height


def point_on_path(points, fraction):
    fraction = max(0, min(1, fraction))
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    distance = fraction * sum(lengths)
    for (x1, y1), (x2, y2), length in zip(points, points[1:], lengths):
        if distance <= length:
            portion = distance / length if length else 0
            return x1 + (x2 - x1) * portion, y1 + (y2 - y1) * portion
        distance -= length
    return points[-1]


def caption(draw, scene, index, total, t=0):
    draw.rectangle((0, 582, W, H), fill=(INK[0], INK[1], INK[2], 230))
    draw.rectangle((75, 608, 85, 687), fill=(255, 146, 105, 255))
    if "_subtitles" in scene:
        draw.text((109, 590), scene["caption"], font=font(24), fill=(171, 203, 234, 255))
        text = next((cue["text"] for cue in scene["_subtitles"]
                     if cue["start"] <= t < cue["end"]), "")
        lines, current = [], ""
        for word in text.split():
            trial = (current + " " + word).strip()
            if draw.textbbox((0, 0), trial, font=font(34))[2] > 1050 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        y = 626 if len(lines) > 1 else 644
        for line in lines:
            draw.text((109, y), line, font=font(34), fill=(255, 255, 255, 255))
            y += 40
        draw.text((1138, 38), f"{index:02d} / {total:02d}", font=font(20), fill=(14, 50, 88, 255))
        return
    words = scene["caption"].split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=font(39))[2] > 1050 and current:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    y = 609 if len(lines) > 1 else 628
    for line in lines:
        draw.text((109, y), line, font=font(39), fill=(255, 255, 255, 255))
        y += 48
    draw.text((1138, 38), f"{index:02d} / {total:02d}", font=font(20), fill=(14, 50, 88, 255))


def overlay(frame, scene, t, dx=37, dy=20):
    scene_id = scene["id"]
    layer = Image.new("RGBA", (OUTPUT_W, OUTPUT_H), (0, 0, 0, 0))
    d = CanvasDraw(layer)

    if scene_id in {"home_network", "send"}:
        pulse = (math.sin(t * math.tau / 2.2) + 1) / 2
        for radius in (38, 67, 97):
            r = radius + int(pulse * 11)
            d.arc((1055-r, 439-r, 1055+r, 439+r), 205, 335, fill=(31, 98, 226, int(65 + 80 * (1-pulse))), width=5)
        if scene_id == "send":
            x, y = point_on_path([(320, 405), (555, 315), (795, 365), (1000, 438)], (t % 3.8) / 3.8)
            envelope(d, x-31, y-22, 62, color=BLUE, body=(255, 250, 238, 255))

    elif scene_id == "connected_networks":
        x, y = point_on_path([(160, 465), (340, 570), (700, 584), (955, 500), (1100, 570)], (t % 5.5) / 5.5)
        envelope(d, x-34, y-24, 68, body=(255, 250, 238, 255))

    elif scene_id == "packets":
        frame = Image.blend(frame, Image.new("RGB", (OUTPUT_W, OUTPUT_H), CREAM), .83)
        d.text((145, 170), "A SHORT TEXT", font=font(34), fill=INK)
        d.text((785, 170), "A PHOTO", font=font(34), fill=INK)
        bob = int(8 * math.sin(t * math.tau / 2.4))
        envelope(d, 252, 305 + bob, 170, color=BLUE, body=(255, 255, 255, 255))
        d.text((235, 444), '"Meet me at six"', font=font(28), fill=INK)
        for i in range(9):
            phase = t * math.tau / 2.4 + i * .45
            xx = 775 + (i % 3) * 112
            yy = 268 + (i // 3) * 75 + int(5 * math.sin(phase))
            envelope(d, xx, yy, 82, color=BLUE if i % 2 else (240, 111, 83), body=(255, 255, 255, 255))

    elif scene_id in {"routers", "service"}:
        points = ([(445, 497), (646, 412), (829, 528), (1076, 397)]
                  if scene_id == "routers" else
                  [(160, 465), (410, 565), (785, 590), (1100, 533)])
        x, y = point_on_path(points, (t % 4.6) / 4.6)
        envelope(d, x-34, y-24, 68, body=(255, 250, 238, 255))

    elif scene_id in {"opening", "delivered"}:
        if scene_id == "opening":
            d.text((700 - (dx-37), 182 - (dy-20)), "Meet me at six", font=font(26), fill=(255, 255, 255, 255))
        else:
            d.text((802 - (dx-37), 242 - (dy-20)), "Meet me at six", font=font(21), fill=(255, 255, 255, 255))

    return Image.alpha_composite(frame.convert("RGBA"), layer)


def render_visual(scenes, output):
    assets = {}
    for scene in scenes:
        name = scene["asset"]
        if name not in assets:
            source = Image.open(ROOT / "assets" / name).convert("RGB")
            assets[name] = ImageOps.fit(source, (OUTPUT_W + round(78 * SCALE),
                                               OUTPUT_H + round(42 * SCALE)),
                                       method=Image.Resampling.LANCZOS)

    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{OUTPUT_W}x{OUTPUT_H}",
               "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
               "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for index, scene in enumerate(scenes, 1):
            print(f"Rendering scene {index}/{len(scenes)}: {scene['id']}", flush=True)
            total_frames = round(scene["duration"] * FPS)
            source = assets[scene["asset"]]
            for frame_num in range(total_frames):
                t = frame_num / FPS
                dx = int(37 + 27 * math.sin(t / max(scene["duration"], 1) * math.pi))
                dy = int(20 + 13 * math.sin(t / max(scene["duration"], 1) * math.pi * 1.3))
                crop_x, crop_y = round(dx * SCALE), round(dy * SCALE)
                frame = source.crop((crop_x, crop_y, crop_x + OUTPUT_W, crop_y + OUTPUT_H))
                frame = overlay(frame, scene, t, dx, dy)
                draw = CanvasDraw(frame)
                caption(draw, scene, index, len(scenes), t)
                proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("FFmpeg could not encode the video")
    except BaseException:
        proc.kill()
        proc.wait()
        raise


def add_audio(video, narration, music, output, duration):
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video)]
    streams = []
    if narration:
        command += ["-i", str(narration)]
        streams.append("[1:a]volume=1,apad[n]")
    if music:
        command += ["-stream_loop", "-1", "-i", str(music)]
        index = 2 if narration else 1
        streams.append(f"[{index}:a]volume=0.12[m]")
    if narration and music:
        streams.append("[n][m]amix=inputs=2:duration=longest:dropout_transition=0[a]")
        label = "[a]"
    else:
        label = "[n]" if narration else "[m]"
    command += ["-filter_complex", ";".join(streams), "-map", "0:v:0", "-map", label,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(duration),
                "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True)


def audio_duration(path):
    if not shutil.which("ffprobe"):
        result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path)],
                                capture_output=True, text=True)
        match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
        if not match:
            raise RuntimeError(f"Could not determine audio duration: {path.name}")
        hours, minutes, seconds = map(float, match.groups())
        return hours * 3600 + minutes * 60 + seconds
    value = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip()
    return float(value)


def add_scene_audio(video, scenes, folder, music, output):
    """Pad each voice clip within its own scene so later scenes stay in sync."""
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video)]
    filters = []
    for index, scene in enumerate(scenes, 1):
        command += ["-i", str(folder / (scene["id"] + ".mp3"))]
        duration = scene["duration"]
        filters.append(f"[{index}:a]aresample=44100,aformat=channel_layouts=stereo,"
                       f"apad,atrim=duration={duration},"
                       f"asetpts=PTS-STARTPTS[s{index}]")
    labels = "".join(f"[s{i}]" for i in range(1, len(scenes) + 1))
    filters.append(f"{labels}concat=n={len(scenes)}:v=0:a=1,"
                   "loudnorm=I=-16:TP=-1.5:LRA=7[n]")
    duration = sum(scene["duration"] for scene in scenes)
    if music:
        command += ["-stream_loop", "-1", "-i", str(music)]
        filters.append(f"[{len(scenes)+1}:a]atrim=duration={duration},"
                       "loudnorm=I=-24:TP=-3:LRA=7,volume=0.25,"
                       f"afade=t=in:d=1.5,afade=t=out:st={max(0, duration-3)}:d=3[m]")
        filters.append("[n][m]amix=inputs=2:duration=first:dropout_transition=0,volume=2,"
                       "alimiter=limit=0.95:level=false[a]")
        label = "[a]"
    else:
        label = "[n]"
    command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", label,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", str(duration),
                "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True)


def main():
    global OUTPUT_W, OUTPUT_H, SCALE, FPS, CRF, PRESET
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--narration", type=Path)
    parser.add_argument("--scene-audio-dir", type=Path,
                        help="MP3 files named after each scene ID, made by generate_narration.py")
    parser.add_argument("--music", type=Path)
    parser.add_argument("--subtitles", type=Path, help="Timed subtitles JSON from prepare_subtitles.py")
    parser.add_argument("--output", type=Path, default=ROOT / "preview-silent.mp4")
    parser.add_argument("--width", type=int, default=W, help="Output width for a 16:9 video")
    parser.add_argument("--height", type=int, default=H, help="Output height for a 16:9 video")
    parser.add_argument("--fps", type=int, default=FPS, help="Output frame rate, from 1 to 60")
    parser.add_argument("--crf", type=int, default=CRF, help="H.264 quality; lower is higher quality")
    parser.add_argument("--preset", choices=("ultrafast", "superfast", "veryfast", "faster",
                                            "fast", "medium", "slow"), default=PRESET)
    args = parser.parse_args()
    if (args.width < 320 or args.height < 180 or args.width % 2 or args.height % 2
            or args.width * H != args.height * W):
        parser.error("Choose even 16:9 dimensions, at least 320x180")
    if not 1 <= args.fps <= 60 or not 0 <= args.crf <= 51:
        parser.error("Frame rate must be 1–60 and CRF must be 0–51")
    OUTPUT_W, OUTPUT_H, FPS = args.width, args.height, args.fps
    SCALE, CRF, PRESET = OUTPUT_W / W, args.crf, args.preset
    font.cache_clear()
    if args.narration and args.scene_audio_dir:
        parser.error("Use either --narration or --scene-audio-dir")
    if args.narration or args.music:
        if not all(path.exists() for path in (args.narration, args.music) if path):
            parser.error("A specified audio file was not found")
    scenes = json.loads((ROOT / "scenes.json").read_text(encoding="utf-8"))
    if args.subtitles:
        subtitles = json.loads(args.subtitles.read_text(encoding="utf-8"))
        for scene in scenes:
            timing = subtitles[scene["id"]]
            scene["duration"] = timing["duration"]
            scene["_subtitles"] = timing["cues"]
    if args.scene_audio_dir:
        for scene in scenes:
            clip = args.scene_audio_dir / (scene["id"] + ".mp3")
            if not clip.exists():
                parser.error(f"Missing scene audio: {clip}")
            # Leave a breath after each phrase, and extend scenes when needed.
            scene["duration"] = max(scene["duration"],
                                    math.ceil((audio_duration(clip) + 0.8) * FPS) / FPS)
    duration = sum(scene["duration"] for scene in scenes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.narration or args.music or args.scene_audio_dir:
        with tempfile.TemporaryDirectory() as folder:
            silent = Path(folder) / "silent.mp4"
            render_visual(scenes, silent)
            if args.scene_audio_dir:
                add_scene_audio(silent, scenes, args.scene_audio_dir, args.music, args.output)
            else:
                add_audio(silent, args.narration, args.music, args.output, duration)
    else:
        render_visual(scenes, args.output)
    print(f"Saved {args.output} ({duration}s, {OUTPUT_W}x{OUTPUT_H}, {FPS} fps)")


if __name__ == "__main__":
    main()
