"""Generate one ElevenLabs voice clip per scene, ready for precise video timing.

Load ELEVENLABS_API_KEY from the private .env beside this script, or from the
process environment. The default George voice ID is from ElevenLabs' API
quickstart; use --voice-id to select another voice available to your account.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"


def request(method, path, key, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"xi-api-key": key, "Accept": "audio/mpeg" if data else "application/json"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        # Do not print response bodies: they may contain sensitive information.
        raise RuntimeError(f"ElevenLabs HTTP {exc.code}: request failed") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice-id", default=DEFAULT_VOICE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "audio")
    parser.add_argument("--generate", action="store_true", help="Spend credits to create missing clips")
    args = parser.parse_args()
    scenes = json.loads((ROOT / "scenes.json").read_text(encoding="utf-8"))
    pending = [(scene["id"], scene["narration"]) for scene in scenes
               if not (args.output_dir / (scene["id"] + ".mp3")).exists()]
    characters = sum(len(text) for _, text in pending)
    print(f"{len(pending)} missing scenes, {characters:,} characters; model eleven_flash_v2_5")
    if not args.generate or not pending:
        print("Preview only; pass --generate to create missing clips.")
        return

    # Auditing existing clips should not load the network SDK or require it.
    from dotenv import load_dotenv
    from elevenlabs import ElevenLabs
    from elevenlabs.core.api_error import ApiError

    load_dotenv(ROOT / ".env", override=False, encoding="utf-8-sig", interpolate=False)
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        parser.error("Set ELEVENLABS_API_KEY in the local .env or process environment")
    try:
        subscription = json.loads(request("GET", "/user/subscription", key))
    except RuntimeError as exc:
        if "HTTP 401:" not in str(exc) and "HTTP 403:" not in str(exc):
            raise
        # A restricted TTS key may intentionally lack permission to view usage.
        print("Balance lookup is restricted for this key; using its TTS credit limit.")
        subscription = {}
    used, limit = subscription.get("character_count"), subscription.get("character_limit")
    if isinstance(used, int) and isinstance(limit, int):
        remaining = max(0, limit - used)
        print(f"Reported remaining characters: {remaining:,}")
        if characters > remaining:
            parser.error("The narration exceeds the reported remaining balance")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    client = ElevenLabs(api_key=key, timeout=180)
    for scene_id, sentence in pending:
        output = args.output_dir / (scene_id + ".mp3")
        temporary = output.with_suffix(".mp3.part")
        try:
            result = client.text_to_speech.convert_with_timestamps(
                voice_id=args.voice_id, text=sentence,
                model_id="eleven_flash_v2_5", output_format="mp3_44100_128")
            temporary.write_bytes(base64.b64decode(result.audio_base_64))
            if not temporary.stat().st_size:
                raise RuntimeError("ElevenLabs returned an empty audio clip")
            temporary.replace(output)
            alignment = result.alignment or result.normalized_alignment
            if alignment is not None:
                output.with_suffix(".alignment.json").write_text(
                    json.dumps(alignment.model_dump(by_alias=True), ensure_ascii=False), encoding="utf-8")
        except ApiError as exc:
            detail = exc.body.get("detail", {}) if isinstance(exc.body, dict) else {}
            status = detail.get("status", "request_failed") if isinstance(detail, dict) else "request_failed"
            status = "".join(c for c in str(status) if c.isalnum() or c == "_")[:80]
            raise RuntimeError(f"ElevenLabs HTTP {exc.status_code}: {status}") from None
        if shutil.which("ffprobe"):
            duration = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                                "format=duration", "-of", "default=nw=1:nk=1",
                                                str(output)], text=True).strip()
            print(f"{scene_id}: {duration}s", flush=True)
        else:
            print(f"{scene_id}: saved (duration will be checked before rendering)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
