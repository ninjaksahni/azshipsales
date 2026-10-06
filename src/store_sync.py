from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.github_store import GitHubStoreError, download_bytes, upload_bytes
from src.store_cache import store_to_json_bytes

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
    return {
        "token": token,
        "owner": owner,
        "repo": repo,
        "branch": str(section.get("branch", "appdata")).strip() or "appdata",
        "path": str(section.get("path", "aggregates.json")).strip() or "aggregates.json",
    }


def remote_store_enabled() -> bool:
    return get_github_store_config() is not None


def _write_bytes(path: Path, payload: bytes) -> None:
    from src.store import restore_store_from_bytes

    restore_store_from_bytes(payload, path)


def hydrate_local_store(path: Path) -> bool:
    """
    Pull remote aggregates into the local path when configured.
    Returns True if a remote object was applied or pushed.
    """
    cfg = get_github_store_config()
    if not cfg:
        _set_sync_error(None)
        return False

    try:
        remote_hit = download_bytes(cfg)
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))
        return False

    from src.store import load_store, new_store

    local = load_store(path) if path.exists() else new_store()

    if remote_hit is None:
        if local.get("skus"):
            push_store_snapshot(local, path)
        _set_sync_error(None)
        return False

    remote_bytes, _sha = remote_hit
    try:
        remote = json.loads(remote_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _set_sync_error(f"Remote aggregates JSON is invalid: {exc}")
        return False
    if not isinstance(remote, dict):
        _set_sync_error("Remote aggregates must be a JSON object.")
        return False

    if not local.get("skus"):
        _write_bytes(path, remote_bytes)
        _set_sync_error(None)
        return True

    local_ts = local.get("last_updated") or ""
    remote_ts = remote.get("last_updated") or ""
    if local_ts > remote_ts:
        push_store_snapshot(local, path)
        _set_sync_error(None)
        return True

    _write_bytes(path, remote_bytes)
    _set_sync_error(None)
    return True


def push_store_snapshot(store: dict[str, Any], path: Path | None = None) -> None:
    cfg = get_github_store_config()
    if not cfg:
        return

    payload = store_to_json_bytes(store)
    try:
        remote_hit = download_bytes(cfg)
        sha = remote_hit[1] if remote_hit else None
        upload_bytes(cfg, payload, sha=sha)
        _set_sync_error(None)
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))
