#!/usr/bin/env python3
"""Create a local PKCE authorization session for the unlisted-video uploader.

The OAuth client and resulting token are intentionally kept under .secrets/,
which is ignored by Git.  The only requested Google scope is youtube.upload.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / ".secrets" / "youtube-oauth-client.json"
TOKEN_PATH = ROOT / ".secrets" / "youtube-oauth-token.json"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def main() -> int:
    if not CLIENT_PATH.is_file():
        print(f"Missing ignored OAuth client: {CLIENT_PATH}", file=sys.stderr)
        return 2

    client = json.loads(CLIENT_PATH.read_text(encoding="utf-8"))["installed"]
    verifier = b64url(secrets.token_bytes(48))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    expected_state = secrets.token_urlsafe(32)
    result: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if parsed.path != "/" or query.get("state", [""])[0] != expected_state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid OAuth callback.")
                return
            if "error" in query:
                result["error"] = query["error"][0]
            elif "code" in query:
                result["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h1>YouTube authorization received.</h1>"
                b"<p>You may close this tab and return to Codex.</p>"
            )

        def log_message(self, *_args: object) -> None:
            return

    server = HTTPServer(("0.0.0.0", 0), Callback)
    redirect_uri = f"http://localhost:{server.server_port}/"
    parameters = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": expected_state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    print("Open this URL in a browser signed into the intended YouTube channel:", flush=True)
    print(client["auth_uri"] + "?" + urllib.parse.urlencode(parameters), flush=True)
    print("Waiting for the local OAuth callback...", flush=True)
    server.handle_request()
    server.server_close()

    if "error" in result:
        print(f"Authorization was not granted: {result['error']}", file=sys.stderr)
        return 3
    if "code" not in result:
        print("Authorization callback lacked a code.", file=sys.stderr)
        return 4

    payload = urllib.parse.urlencode(
        {
            "code": result["code"],
            "client_id": client["client_id"],
            "client_secret": client.get("client_secret", ""),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    ).encode("ascii")
    request = urllib.request.Request(
        client["token_uri"], payload, {"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.load(response)
    TOKEN_PATH.write_text(json.dumps(token, indent=2) + "\n", encoding="utf-8")
    TOKEN_PATH.chmod(0o600)
    print(f"Authorization succeeded; token stored at {TOKEN_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
