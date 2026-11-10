"""Generate three original instrumental music previews for the explainer."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from elevenlabs.core.api_error import ApiError

ROOT = Path(__file__).resolve().parent
STYLES = {
    "warm-ambient": "Warm soft ambient instrumental, airy synth pads, delicate marimba notes, gentle optimistic curiosity, no drums, spacious and calm.",
    "gentle-piano": "Gentle felt piano instrumental, warm sustained chords, sparse original melody, subtle soft pads, relaxed optimistic educational mood, no drums.",
    "soft-electronic": "Soft minimal electronic instrumental, mellow rounded synth plucks, very light muted pulse, warm bass, friendly curious technology explainer mood, 80 BPM, no sharp percussion.",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=STYLES)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", encoding="utf-8-sig", interpolate=False)
    client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY", "").strip(), timeout=300)
    folder = ROOT / "music"
    folder.mkdir(exist_ok=True)
    styles = [args.style] if args.style else STYLES
    for style in styles:
        output = folder / f"{style}-{args.seconds}s.mp3"
        if output.exists() and output.stat().st_size:
            print(f"Reusing {output.name}", flush=True)
            continue
        print(f"Generating {style}: {args.seconds}s", flush=True)
        try:
            audio = client.music.compose(
                prompt=STYLES[style] + " Background underscore beneath spoken narration. Restrained dynamics, no vocals, no dramatic builds. Original composition, no references to existing songs or artists.",
                music_length_ms=args.seconds * 1000,
                model_id="music_v2_5", force_instrumental=True)
            temporary = output.with_suffix(".mp3.part")
            with temporary.open("wb") as stream:
                for chunk in audio:
                    stream.write(chunk)
            if not temporary.stat().st_size:
                raise RuntimeError("Empty music response")
            temporary.replace(output)
            print(f"Saved {output.name}", flush=True)
        except ApiError as exc:
            # Never echo headers, credentials, or a raw API response.
            print(f"Music generation failed (HTTP {exc.status_code}).", flush=True)
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
