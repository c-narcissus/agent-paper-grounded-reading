import argparse
import socket
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def find_available_port(host: str, start_port: int, max_tries: int) -> int:
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_tries - 1}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-port-tries", type=int, default=25)
    parser.add_argument("--url-file")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    port = find_available_port(args.host, args.port, args.max_port_tries)
    url = f"http://{args.host}:{port}/"
    print(f"Serving {root}")
    print(f"Open: {url}")

    if args.url_file:
        url_file = Path(args.url_file).expanduser().resolve()
        url_file.parent.mkdir(parents=True, exist_ok=True)
        url_file.write_text(url, encoding="utf-8")

    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((args.host, port), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
