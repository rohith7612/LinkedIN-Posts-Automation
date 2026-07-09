"""Step 6: upload the day's infographic image(s) and publish the LinkedIn post.

Uses LinkedIn's Posts API (/rest/posts) + Images API (/rest/images). LinkedIn
occasionally revs its API -- if calls start failing with version errors, check
https://learn.microsoft.com/linkedin/ (Microsoft hosts LinkedIn's API docs) and
bump LINKEDIN_API_VERSION in config.py.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import LINKEDIN_API_VERSION, LINKEDIN_TOKEN_FILE, today_dir

API_BASE = "https://api.linkedin.com/rest"


def _load_token() -> dict:
    if not LINKEDIN_TOKEN_FILE.exists():
        raise RuntimeError(
            "No LinkedIn token found. Run: python src/linkedin_auth.py (one-time setup)."
        )
    with open(LINKEDIN_TOKEN_FILE, "r", encoding="utf-8") as f:
        token = json.load(f)

    expires_at = datetime.fromisoformat(token["expires_at"])
    if datetime.now(timezone.utc) >= expires_at:
        raise RuntimeError(
            "LinkedIn access token has expired. Run: python src/linkedin_auth.py to reauthorize."
        )
    return token


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _raise_with_body(resp: requests.Response):
    """requests' default raise_for_status() swallows LinkedIn's error detail --
    surface it so failures are actually debuggable."""
    if resp.status_code >= 400:
        raise RuntimeError(
            f"LinkedIn API error {resp.status_code} for {resp.request.method} {resp.request.url}\n"
            f"Response body: {resp.text}"
        )


def _upload_image(image_path: Path, access_token: str, member_urn: str) -> str:
    init_resp = requests.post(
        f"{API_BASE}/images?action=initializeUpload",
        headers={**_headers(access_token), "Content-Type": "application/json"},
        json={"initializeUploadRequest": {"owner": member_urn}},
        timeout=30,
    )
    _raise_with_body(init_resp)
    value = init_resp.json()["value"]
    upload_url, image_urn = value["uploadUrl"], value["image"]

    with open(image_path, "rb") as f:
        put_resp = requests.put(
            upload_url,
            data=f.read(),
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )
    _raise_with_body(put_resp)

    return image_urn


def _build_post_body(member_urn: str, commentary: str, image_urns: list[str]) -> dict:
    body = {
        "author": member_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
    }

    if len(image_urns) == 1:
        body["content"] = {"media": {"id": image_urns[0]}}
    else:
        body["content"] = {
            "multiImage": {"images": [{"id": urn} for urn in image_urns]}
        }
    return body


def publish_post(image_paths: list[Path], commentary: str) -> str:
    token = _load_token()
    access_token, member_urn = token["access_token"], token["member_urn"]

    image_urns = [_upload_image(p, access_token, member_urn) for p in image_paths]

    body = _build_post_body(member_urn, commentary, image_urns)
    post_resp = requests.post(
        f"{API_BASE}/posts",
        headers={**_headers(access_token), "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    _raise_with_body(post_resp)
    post_id = post_resp.headers.get("x-restli-id", "(unknown id)")
    return post_id


def main():
    day_dir = today_dir()
    infographics_dir = day_dir / "infographics"
    image_paths = sorted(
        p for p in infographics_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )

    if not image_paths:
        print(f"No infographic images found in {infographics_dir}. "
              "Generate them in NotebookLM and save them there first.")
        return

    description_path = day_dir / "description.txt"
    if not description_path.exists():
        print("No description.txt found -- run describe.py first (or pipeline.py phase2).")
        return
    commentary = description_path.read_text(encoding="utf-8")

    print(f"Uploading {len(image_paths)} image(s) and publishing to LinkedIn...")
    post_id = publish_post(image_paths, commentary)
    print(f"Published. Post id: {post_id}")

    log_path = day_dir / "post_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(
            {"post_id": post_id, "images": [str(p) for p in image_paths], "posted_at": datetime.now(timezone.utc).isoformat()},
            f,
            indent=2,
        )


if __name__ == "__main__":
    main()
