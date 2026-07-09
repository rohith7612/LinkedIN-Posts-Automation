"""One-time (and re-run every ~60 days) LinkedIn OAuth setup.

Run this manually:  python src/linkedin_auth.py
It opens your browser to LinkedIn's consent screen, catches the redirect on a
local server, exchanges the code for an access token, looks up your member id,
and saves everything to data/linkedin_token.json for linkedin_post.py to use.
"""
import json
import secrets
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from config import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_REDIRECT_URI,
    LINKEDIN_TOKEN_FILE,
)

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPES = "openid profile w_member_social"

_captured = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server naming convention
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        _captured["code"] = params.get("code", [None])[0]
        _captured["state"] = params.get("state", [None])[0]
        _captured["error"] = params.get("error_description", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if _captured["code"]:
            self.wfile.write(b"<html><body><h2>LinkedIn authorized. You can close this tab and return to the terminal.</h2></body></html>")
        else:
            self.wfile.write(b"<html><body><h2>Authorization failed. Check the terminal for details.</h2></body></html>")

    def log_message(self, format, *args):  # noqa: A002 - silence default logging
        pass


def _require_app_credentials():
    if not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        raise RuntimeError(
            "LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET are not set. "
            "Fill them in .env after creating your LinkedIn Developer App (see README)."
        )


def run_auth_flow():
    _require_app_credentials()

    state = secrets.token_urlsafe(16)
    auth_url = f"{AUTH_URL}?" + urlencode(
        {
            "response_type": "code",
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
        }
    )

    parsed_redirect = urlparse(LINKEDIN_REDIRECT_URI)
    host, port = parsed_redirect.hostname, parsed_redirect.port or 80

    print(f"Opening browser for LinkedIn authorization...\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer((host, port), _CallbackHandler)
    print(f"Waiting for LinkedIn redirect on {LINKEDIN_REDIRECT_URI} ...")
    server.handle_request()  # blocks until the one callback request arrives

    if _captured.get("error"):
        raise RuntimeError(f"LinkedIn authorization failed: {_captured['error']}")
    if _captured.get("state") != state:
        raise RuntimeError("State mismatch -- possible CSRF, aborting.")
    code = _captured.get("code")
    if not code:
        raise RuntimeError("No authorization code received.")

    token_resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 60 * 24 * 3600)

    userinfo_resp = requests.get(
        USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=30
    )
    userinfo_resp.raise_for_status()
    member_id = userinfo_resp.json()["sub"]
    member_urn = f"urn:li:person:{member_id}"

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

    LINKEDIN_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LINKEDIN_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"access_token": access_token, "expires_at": expires_at, "member_urn": member_urn},
            f,
            indent=2,
        )

    print(f"Success. Token saved to {LINKEDIN_TOKEN_FILE}")
    print(f"Member URN: {member_urn}")
    print(f"Token expires: {expires_at} (LinkedIn tokens last ~60 days -- rerun this script when it expires)")


if __name__ == "__main__":
    run_auth_flow()
