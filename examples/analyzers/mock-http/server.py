from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AnalyzerHandler(BaseHTTPRequestHandler):
    """Tiny HTTP analyzer for local integration smoke tests."""

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length:
            self.rfile.read(content_length)

        payload = {
            "schema_version": "vision-roi-guard.v1",
            "result": "safe",
            "reason": "mock_roi_clear",
            "seen_objects": [],
            "confidence": 1.0,
            "duration_sec": 0.0,
        }
        body = json.dumps(payload).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AnalyzerHandler)
    print(f"Serving mock analyzer on http://{args.host}:{args.port}/analyze")
    server.serve_forever()


if __name__ == "__main__":
    main()
