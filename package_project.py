"""Create a shareable project ZIP, always excluding local secrets and tools."""

import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache",
            ".mypy_cache", "work", "tmp", "temp"}
TEMP_SUFFIXES = {".zip", ".pyc", ".part", ".download", ".tmp", ".temp", ".log"}


def excluded(path):
    return (any(part in EXCLUDED or part == ".env" or part.startswith(".env.")
                for part in path.parts)
            or path.suffix.lower() in TEMP_SUFFIXES
            or path.name.startswith("~$"))


def package(output):
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for folder, directories, files in os.walk(ROOT, followlinks=False):
            base = Path(folder)
            directories[:] = [name for name in directories
                              if not excluded((base / name).relative_to(ROOT))
                              and not (base / name).is_symlink()]
            for name in sorted(files):
                source = base / name
                relative = source.relative_to(ROOT)
                if not excluded(relative) and not source.is_symlink():
                    archive.write(source, Path(ROOT.name) / relative)


if __name__ == "__main__":
    output = ROOT.parent / "message-explainer.zip"
    package(output)
    print(f"Saved {output.name}; local secrets and environments excluded.")
