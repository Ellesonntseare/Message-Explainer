"""Build accurate phrase subtitles from saved ElevenLabs character timings."""

import json
import math
import re
from pathlib import Path

from render_video import FPS, audio_duration

ROOT = Path(__file__).resolve().parent


def words_from_alignment(data):
    if "words" in data:
        return [{"text": w["text"].strip(), "start": w["start"], "end": w["end"]}
                for w in data["words"] if w["text"].strip()]
    text = "".join(data["characters"])
    starts = data["character_start_times_seconds"]
    ends = data["character_end_times_seconds"]
    return [{"text": m.group(), "start": starts[m.start()], "end": ends[m.end()-1]}
            for m in re.finditer(r"\S+", text)]


def cues_from_words(words, duration):
    groups, current = [], []
    for word in words:
        if current and (len(current) >= 8
                        or len(" ".join(w["text"] for w in current + [word])) > 72
                        or word["end"] - current[0]["start"] > 4
                        or word["start"] - current[-1]["end"] > .45):
            groups.append(current)
            current = []
        current.append(word)
        if word["text"].rstrip('"\u201d').endswith((".", "!", "?", ";")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    cues = []
    for index, group in enumerate(groups):
        next_start = groups[index+1][0]["start"] if index+1 < len(groups) else duration
        cues.append({"start": round(group[0]["start"], 3),
                     "end": round(min(next_start, group[-1]["end"] + .15, duration), 3),
                     "text": " ".join(w["text"] for w in group)})
    return cues


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def main():
    scenes = json.loads((ROOT / "scenes.json").read_text(encoding="utf-8"))
    subtitles, srt, offset, number = {}, [], 0, 1
    for scene in scenes:
        stem = ROOT / "audio" / scene["id"]
        clip_duration = audio_duration(stem.with_suffix(".mp3"))
        # Keep a short breath after every phrase; avoid the rough animatic's long gaps.
        duration = max(4, math.ceil((clip_duration + .8) * FPS) / FPS)
        data = json.loads(stem.with_suffix(".alignment.json").read_text(encoding="utf-8"))
        cues = cues_from_words(words_from_alignment(data), duration)
        subtitles[scene["id"]] = {"duration": duration, "audio_duration": clip_duration,
                                   "start": offset, "cues": cues}
        for cue in cues:
            srt.append(f"{number}\n{timestamp(offset+cue['start'])} --> "
                       f"{timestamp(offset+cue['end'])}\n{cue['text']}\n")
            number += 1
        offset += duration
    (ROOT / "subtitles.json").write_text(json.dumps(subtitles, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "final.srt").write_text("\n".join(srt), encoding="utf-8")
    print(f"Prepared {number-1} subtitle cues across {len(scenes)} scenes; {offset:.2f}s total")


if __name__ == "__main__":
    main()
