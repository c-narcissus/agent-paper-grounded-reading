import argparse
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    os.chdir(root)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Serving {root}")
    print(f"Open: {url}")

    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), SimpleHTTPRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
