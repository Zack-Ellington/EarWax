"""Runtime preflight for the local EarWax + llama.cpp setup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
import sys
from typing import Sequence
from urllib import error, request


LLAMA_CPP_ROOT = Path(r"C:\Users\zaell\llama.cpp")
DEFAULT_VENV_PYTHON = LLAMA_CPP_ROOT / ".venv" / "Scripts" / "python.exe"
DEFAULT_VULKAN_SERVER = LLAMA_CPP_ROOT / "build-vulkan" / "bin" / "llama-server.exe"
DEFAULT_QWEN_GGUF = (
    LLAMA_CPP_ROOT
    / "models-gguf"
    / "unsloth"
    / "Qwen3-4B-Instruct-2507-GGUF"
    / "Qwen3-4B-Instruct-2507-Q4_K_S.gguf"
)


@dataclass(slots=True)
class RuntimeContext:
    expected_python: Path | None
    server_executable: Path | None
    model_path: Path | None
    base_url: str
    model_name: str
    original_argv: list[str]


def default_venv_python() -> str:
    return str(DEFAULT_VENV_PYTHON) if DEFAULT_VENV_PYTHON.exists() else ""


def default_server_executable() -> str:
    return str(DEFAULT_VULKAN_SERVER) if DEFAULT_VULKAN_SERVER.exists() else ""


def default_model_path() -> str:
    return str(DEFAULT_QWEN_GGUF) if DEFAULT_QWEN_GGUF.exists() else ""


def default_model_name() -> str:
    model_path = default_model_path()
    return model_path or "Qwen3-4B"


def ensure_runtime_ready(
    *,
    expected_python: str | None,
    server_executable: str | None,
    model_path: str | None,
    base_url: str,
    model_name: str,
    original_argv: Sequence[str],
) -> None:
    context = RuntimeContext(
        expected_python=_coerce_path(expected_python),
        server_executable=_coerce_path(server_executable),
        model_path=_coerce_path(model_path),
        base_url=base_url.rstrip("/"),
        model_name=model_name,
        original_argv=list(original_argv),
    )
    _ensure_expected_python(context)
    _ensure_server_binary(context)
    _ensure_vulkan_build(context)
    _ensure_model_path(context)
    _ensure_server_available(context)


def build_server_command(
    *,
    server_executable: Path,
    model_path: Path,
    host: str = "127.0.0.1",
    port: int = 8080,
    ctx_size: int = 8192,
    threads: int = 6,
    threads_batch: int = 8,
    batch_size: int = 512,
    ubatch_size: int = 256,
    n_gpu_layers: int = 99,
) -> list[str]:
    return [
        str(server_executable),
        "-m",
        str(model_path),
        "--host",
        host,
        "--port",
        str(port),
        "--ctx-size",
        str(ctx_size),
        "--parallel",
        "1",
        "--threads",
        str(threads),
        "--threads-batch",
        str(threads_batch),
        "--batch-size",
        str(batch_size),
        "--ubatch-size",
        str(ubatch_size),
        "--n-gpu-layers",
        str(n_gpu_layers),
        "--flash-attn",
        "on",
    ]


def launch_server(*, server_executable: Path, model_path: Path) -> int:
    completed = subprocess.run(
        build_server_command(server_executable=server_executable, model_path=model_path),
        check=False,
    )
    return completed.returncode


def _coerce_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None
    return Path(raw_value).expanduser().resolve()


def _ensure_expected_python(context: RuntimeContext) -> None:
    if context.expected_python is None:
        return

    actual = Path(sys.executable).resolve()
    if actual == context.expected_python:
        return

    rerun_parts = [
        str(context.expected_python),
        "memory_system\\app.py",
        *context.original_argv,
    ]
    raise RuntimeError(
        "EarWax must run from the local Windows venv interpreter.\n"
        f"Current interpreter: {actual}\n"
        f"Expected interpreter: {context.expected_python}\n"
        "Rerun with:\n"
        + " ".join(_quote(part) for part in rerun_parts)
    )


def _ensure_server_binary(context: RuntimeContext) -> None:
    if context.server_executable is None:
        return
    if not context.server_executable.exists():
        raise RuntimeError(
            f"Configured llama.cpp server executable was not found: {context.server_executable}"
        )


def _ensure_vulkan_build(context: RuntimeContext) -> None:
    if context.server_executable is None:
        return

    cache_path = context.server_executable.parents[1] / "CMakeCache.txt"
    if not cache_path.exists():
        raise RuntimeError(f"Could not locate CMakeCache.txt next to {context.server_executable}")

    cache_text = cache_path.read_text(encoding="utf-8", errors="ignore")
    if "GGML_VULKAN:BOOL=ON" not in cache_text:
        raise RuntimeError(
            "The configured llama.cpp build is not Vulkan-enabled.\n"
            f"Checked: {cache_path}\n"
            "Expected to find: GGML_VULKAN:BOOL=ON"
        )


def _ensure_model_path(context: RuntimeContext) -> None:
    if context.model_path is None:
        return
    if not context.model_path.exists():
        raise RuntimeError(f"Configured GGUF model was not found: {context.model_path}")


def _ensure_server_available(context: RuntimeContext) -> None:
    models_url = f"{context.base_url}/v1/models"
    try:
        with request.urlopen(models_url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, json.JSONDecodeError):
        raise RuntimeError(
            f"Failed to reach llama.cpp model route '{context.model_name}' at {context.base_url}.\n"
            f"The local server did not answer at {models_url}.\n"
            f"Start the Vulkan server first with:\n{_launch_command_text(context)}"
        )

    model_ids = {
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    }
    accepted_ids = _candidate_model_ids(context)
    if model_ids and model_ids.isdisjoint(accepted_ids):
        raise RuntimeError(
            f"llama.cpp is reachable at {context.base_url}, but model '{context.model_name}' is not listed.\n"
            f"Available models: {', '.join(sorted(model_ids))}"
        )


def _launch_command_text(context: RuntimeContext) -> str:
    if context.server_executable is None or context.model_path is None:
        return "Start the local llama.cpp Vulkan server and retry."
    command = build_server_command(
        server_executable=context.server_executable,
        model_path=context.model_path,
    )
    return " ".join(_quote(part) for part in command)


def _candidate_model_ids(context: RuntimeContext) -> set[str]:
    candidate_ids = {context.model_name}
    if context.model_path is not None:
        candidate_ids.add(str(context.model_path))
        candidate_ids.add(context.model_path.name)
        candidate_ids.add(context.model_path.stem)
    return {candidate for candidate in candidate_ids if candidate}


def _quote(value: str) -> str:
    if " " in value or "\t" in value:
        return f'"{value}"'
    return value
