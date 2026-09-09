#!/usr/bin/env python3
"""
Start the Search Summarizer Web API and Web UI together.

Development (default):
  - FastAPI / Uvicorn on http://127.0.0.1:8000
  - Vite React UI on http://127.0.0.1:4001

Production:
  - Builds the Web UI into web/dist
  - Serves API + SPA from a single Uvicorn process on http://127.0.0.1:8000

Usage:
  python serve.py
  python serve.py --prod
  python serve.py --api-only
  python serve.py --ui-only
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
DEFAULT_UI_PORT = 4001


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _ensure_npm() -> str:
    npm = _which("npm") or _which("npm.cmd")
    if not npm:
        raise SystemExit(
            "npm was not found on PATH. Install Node.js, then re-run serve.py."
        )
    return npm


def _run_npm_install(npm: str) -> None:
    node_modules = WEB_DIR / "node_modules"
    if node_modules.is_dir():
        return
    print("Installing Web UI dependencies (npm install)...")
    subprocess.check_call([npm, "install"], cwd=WEB_DIR)


def _build_web(npm: str) -> None:
    print("Building Web UI (npm run build)...")
    subprocess.check_call([npm, "run", "build"], cwd=WEB_DIR)


def _write_web_env(api_base: str) -> None:
    env_path = WEB_DIR / ".env"
    content = f"VITE_API_BASE_URL={api_base}\n"
    if env_path.exists() and env_path.read_text(encoding="utf-8").strip() == content.strip():
        return
    env_path.write_text(content, encoding="utf-8")
    print(f"Wrote {env_path} -> {api_base}")


def start_api(host: str, port: int, reload: bool) -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    print(f"Starting API  -> http://{host}:{port}")
    print(f"OpenAPI docs  -> http://{host}:{port}/docs")
    return subprocess.Popen(cmd, cwd=ROOT)


def start_ui(npm: str, api_base: str) -> subprocess.Popen:
    _write_web_env(api_base)
    _run_npm_install(npm)
    print(f"Starting Web UI -> http://127.0.0.1:{DEFAULT_UI_PORT}")
    # Use shell=False; on Windows npm.cmd works via which.
    return subprocess.Popen([npm, "run", "dev"], cwd=WEB_DIR)


def start_prod(host: str, port: int) -> int:
    npm = _ensure_npm()
    # Same-origin API calls from the SPA (empty base => relative URLs).
    _write_web_env("")
    _run_npm_install(npm)
    _build_web(npm)

    print(f"Starting production server -> http://{host}:{port}")
    print("API + Web UI are served from the same process (web/dist mounted).")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve Search Summarizer API and Web UI",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Build Web UI and serve API+UI from one Uvicorn process",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Start only the FastAPI server",
    )
    parser.add_argument(
        "--ui-only",
        action="store_true",
        help="Start only the Vite Web UI",
    )
    parser.add_argument("--host", default=DEFAULT_API_HOST, help="API bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT, help="API port")
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable API auto-reload in development",
    )
    args = parser.parse_args()

    if args.prod and (args.api_only or args.ui_only):
        raise SystemExit("--prod cannot be combined with --api-only / --ui-only")

    os.chdir(ROOT)

    if args.prod:
        return start_prod(args.host, args.port)

    processes: list[subprocess.Popen] = []

    def shutdown(*_args) -> None:
        print("\nShutting down...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        deadline = time.time() + 8
        for proc in processes:
            remaining = max(0.1, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    api_base = f"http://{args.host}:{args.port}"

    try:
        if not args.ui_only:
            processes.append(
                start_api(args.host, args.port, reload=not args.no_reload)
            )
            time.sleep(1.0)

        if not args.api_only:
            npm = _ensure_npm()
            processes.append(start_ui(npm, api_base))

        print("\nReady. Press Ctrl+C to stop.\n")
        while True:
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"Process exited with code {code}")
                    shutdown()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
