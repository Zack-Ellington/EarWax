"""Start the local Vulkan-enabled llama.cpp server used by EarWax."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src.runtime import (
    build_server_command,
    default_model_path,
    default_server_executable,
    launch_server,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start the Vulkan-enabled llama.cpp server used by EarWax."
    )
    parser.add_argument(
        "--server-exe",
        default=default_server_executable(),
        help="Path to the Vulkan llama-server executable",
    )
    parser.add_argument(
        "--model-path",
        default=default_model_path(),
        help="Path to the GGUF model to serve",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the launch command without starting the server",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server_exe = Path(args.server_exe).expanduser().resolve()
    model_path = Path(args.model_path).expanduser().resolve()
    command = build_server_command(
        server_executable=server_exe,
        model_path=model_path,
    )

    if args.dry_run:
        print(" ".join(f'"{part}"' if " " in part else part for part in command))
        return 0

    return launch_server(server_executable=server_exe, model_path=model_path)


if __name__ == "__main__":
    raise SystemExit(main())
