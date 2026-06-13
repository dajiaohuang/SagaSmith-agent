#!/usr/bin/env python3
import argparse
import subprocess
import sys

PINNED = {
    "paddleocr": ["paddleocr==3.6.0"],
    "pdf_ocr": ["pypdfium2>=4.30,<5", "paddleocr==3.6.0"],
    "whisper": ["openai-whisper==20250625"],
    "markitdown": ["markitdown>=0.1.0"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install optional multimodal parsing backends")
    parser.add_argument("--backend", choices=["all", *PINNED], default="all")
    parser.add_argument("--upgrade", action="store_true")
    args = parser.parse_args()
    targets = list(PINNED) if args.backend == "all" else [args.backend]
    packages = list(dict.fromkeys(package for target in targets for package in PINNED[target]))
    command = ["uv", "add", "--project", "backend"]
    if args.upgrade:
        command.append("--upgrade")
    return subprocess.call([*command, *packages])


if __name__ == "__main__":
    raise SystemExit(main())
