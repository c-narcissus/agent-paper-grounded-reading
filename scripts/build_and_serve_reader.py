import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"


def resolve_manifest_path(base_dir: Path, value, fallback=None):
    raw_value = value or fallback
    if not raw_value:
        return None
    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def wait_for_url(url_file: Path, timeout_seconds: float):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if url_file.exists():
            url = url_file.read_text(encoding="utf-8").strip()
            if url:
                return url
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for URL file: {url_file}")


def wait_for_http(url: str, timeout_seconds: float):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 400:
                    return response.status
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for reader HTTP response at {url}: {last_error}")


def launch_server(command, log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", encoding="utf-8")
    popen_kwargs = {
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    return subprocess.Popen(command, **popen_kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="Build the static evidence reader and launch a local HTTP server."
    )
    parser.add_argument("--artifact-manifest", required=True, help="reader_artifacts.json path.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-port-tries", type=int, default=25)
    parser.add_argument("--url-file", help="Where to write the live reader URL.")
    parser.add_argument("--log-file", help="Where to write server logs.")
    parser.add_argument("--open", action="store_true", help="Ask the OS browser to open the URL.")
    parser.add_argument("--wait-seconds", type=float, default=15.0)
    args = parser.parse_args()

    artifact_manifest = Path(args.artifact_manifest).expanduser().resolve()
    manifest = json.loads(artifact_manifest.read_text(encoding="utf-8"))
    base_dir = artifact_manifest.parent
    reader_root = resolve_manifest_path(base_dir, manifest.get("reader_output"), "reader_bundle")
    if reader_root is None:
        raise RuntimeError("Unable to resolve reader output directory")

    url_file = Path(args.url_file).expanduser().resolve() if args.url_file else base_dir / "reader_url.txt"
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else base_dir / "reader_server.log"

    build_script = SCRIPTS_DIR / "build_reader_bundle.py"
    serve_script = SCRIPTS_DIR / "serve_bundle.py"

    subprocess.run(
        [sys.executable, str(build_script), "--artifact-manifest", str(artifact_manifest)],
        check=True,
    )

    if url_file.exists():
        url_file.unlink()

    serve_command = [
        sys.executable,
        str(serve_script),
        "--root",
        str(reader_root),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--max-port-tries",
        str(args.max_port_tries),
        "--url-file",
        str(url_file),
    ]
    if args.open:
        serve_command.append("--open")

    process = launch_server(serve_command, log_file)
    url = wait_for_url(url_file, args.wait_seconds)
    status_code = wait_for_http(url, args.wait_seconds)

    print(
        json.dumps(
            {
                "status": "ok",
                "url": url,
                "http_status": status_code,
                "reader_root": str(reader_root),
                "server_pid": process.pid,
                "url_file": str(url_file),
                "log_file": str(log_file),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
