from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_VERSION = "2022-11-28"
USER_AGENT = "azshipsales/1.0"


class GitHubStoreError(Exception):
    pass


def _request(
    cfg: dict[str, str],
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    owner = cfg["owner"]
    repo = cfg["repo"]
    url = f"https://api.github.com/repos/{owner}/{repo}/{path}"
    body = None
    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubStoreError(f"GitHub API {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GitHubStoreError(str(exc)) from exc


def ensure_branch(cfg: dict[str, str]) -> None:
    branch = cfg.get("branch", "appdata")
    owner = cfg["owner"]
    repo = cfg["repo"]
    ref_path = urllib.parse.quote(f"heads/{branch}", safe="/")
    existing = _request(cfg, "GET", f"git/ref/{ref_path}")
    if existing:
        return

    default = _request(cfg, "GET", "git/ref/heads/main")
    if not default:
        default = _request(cfg, "GET", "git/ref/heads/master")
    if not default:
        raise GitHubStoreError("Could not find main or master branch to create app data branch.")

    sha = default["object"]["sha"]
    _request(
        cfg,
        "POST",
        "git/refs",
        {"ref": f"refs/heads/{branch}", "sha": sha},
    )


def download_bytes(cfg: dict[str, str]) -> tuple[bytes, str | None] | None:
    branch = cfg.get("branch", "appdata")
    file_path = cfg.get("path", "aggregates.json")
    quoted = urllib.parse.quote(file_path, safe="/")
    data = _request(cfg, "GET", f"contents/{quoted}?ref={urllib.parse.quote(branch)}")
    if not data:
        return None
    content = data.get("content")
    if not content:
        return None
    raw = base64.b64decode(content)
    sha = data.get("sha")
    return raw, sha if isinstance(sha, str) else None


def upload_bytes(
    cfg: dict[str, str],
    payload: bytes,
    sha: str | None = None,
    *,
    message: str = "Update app data",
) -> None:
    ensure_branch(cfg)
    branch = cfg.get("branch", "appdata")
    file_path = cfg.get("path", "aggregates.json")
    quoted = urllib.parse.quote(file_path, safe="/")
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(payload).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha
    _request(cfg, "PUT", f"contents/{quoted}", body)
