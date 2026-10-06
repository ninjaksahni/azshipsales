from __future__ import annotations

import json
from typing import Any

from src.github_store import GitHubStoreError, download_bytes, upload_bytes

_LAST_SYNC_ERROR: str | None = None


def last_sync_error() -> str | None:
    return _LAST_SYNC_ERROR


def _set_sync_error(message: str | None) -> None:
    global _LAST_SYNC_ERROR
    _LAST_SYNC_ERROR = message


def is_streamlit_cloud() -> bool:
    import os

    return bool(
        os.environ.get("STREAMLIT_SHARING")
        or os.environ.get("STREAMLIT_CLOUD")
        or os.environ.get("USER") == "appuser"
    )


def get_github_store_config() -> dict[str, str] | None:
    try:
        import streamlit as st

        section = st.secrets.get("github_store")
    except Exception:
        return None
    if not section:
        return None
    token = str(section.get("token", "")).strip()
    owner = str(section.get("owner", "")).strip()
    repo = str(section.get("repo", "")).strip()
    if not token or not owner or not repo:
        return None
    geocode_path = str(section.get("geocode_path", "geocode_cache.json")).strip()
    return {
        "token": token,
        "owner": owner,
        "repo": repo,
        "branch": str(section.get("branch", "appdata")).strip() or "appdata",
        "path": str(section.get("path", "aggregates.json")).strip() or "aggregates.json",
        "geocode_path": geocode_path or "geocode_cache.json",
    }


def remote_store_enabled() -> bool:
    return get_github_store_config() is not None


def _cfg_at_path(cfg: dict[str, str], path: str) -> dict[str, str]:
    return {**cfg, "path": path}


def pull_json_file(file_path: str) -> tuple[bytes, str | None] | None:
    cfg = get_github_store_config()
    if not cfg:
        return None
    try:
        return download_bytes(_cfg_at_path(cfg, file_path))
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))
        return None


def push_json_file(file_path: str, payload: bytes, *, message: str) -> None:
    cfg = get_github_store_config()
    if not cfg:
        return
    remote_cfg = _cfg_at_path(cfg, file_path)
    try:
        remote_hit = download_bytes(remote_cfg)
        sha = remote_hit[1] if remote_hit else None
        upload_bytes(remote_cfg, payload, sha=sha, message=message)
        _set_sync_error(None)
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))


def push_json_dict(file_path: str, data: dict[str, Any], *, message: str) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    push_json_file(file_path, payload, message=message)
