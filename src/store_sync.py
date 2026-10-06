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
    geocode_path = str(section.get("geocode_path", "geocode_cache.json")).strip()
    return {
        "token": token,
        "owner": owner,
        "repo": repo,
        "branch": str(section.get("branch", "appdata")).strip() or "appdata",
        "path": str(section.get("path", "aggregates.json")).strip() or "aggregates.json",
        "geocode_path": geocode_path or "geocode_cache.json",
    }


def _cfg_at_path(cfg: dict[str, str], path: str) -> dict[str, str]:
    return {**cfg, "path": path}


def remote_store_enabled() -> bool:
    return get_github_store_config() is not None


def _write_bytes(path: Path, payload: bytes) -> None:
    from src.store import restore_store_from_bytes

    restore_store_from_bytes(payload, path)


def hydrate_local_store(path: Path) -> bool:
    """Pull remote aggregates into the local path when configured."""
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
        upload_bytes(cfg, payload, sha=sha, message="Update shipment aggregates")
        _set_sync_error(None)
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))


def _merge_geocode_dicts(remote: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    if not remote:
        return dict(local)
    if not local:
        return dict(remote)
    return {**remote, **local}


def _write_geocode_file(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")


def hydrate_geocode_cache(path: Path) -> bool:
    cfg = get_github_store_config()
    if not cfg:
        return False

    remote_path = cfg["geocode_path"]
    remote_cfg = _cfg_at_path(cfg, remote_path)

    try:
        remote_hit = download_bytes(remote_cfg)
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))
        return False

    from src.geocode import load_geocode_cache

    local = load_geocode_cache() if path.exists() else {}

    if remote_hit is None:
        if local:
            push_geocode_snapshot(local, path)
        return bool(local)

    remote_bytes, _sha = remote_hit
    try:
        remote = json.loads(remote_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _set_sync_error(f"Remote geocode cache JSON is invalid: {exc}")
        return False
    if not isinstance(remote, dict):
        _set_sync_error("Remote geocode cache must be a JSON object.")
        return False

    merged = _merge_geocode_dicts(remote, local)
    if merged != local:
        _write_geocode_file(path, merged)
        return True
    if merged != remote:
        push_geocode_snapshot(merged, path)
        return True
    return False


def push_geocode_snapshot(cache: dict[str, Any], path: Path | None = None) -> None:
    cfg = get_github_store_config()
    if not cfg:
        return

    remote_cfg = _cfg_at_path(cfg, cfg["geocode_path"])
    payload = json.dumps(cache, indent=2, ensure_ascii=False).encode("utf-8")
    try:
        remote_hit = download_bytes(remote_cfg)
        sha = remote_hit[1] if remote_hit else None
        upload_bytes(remote_cfg, payload, sha=sha, message="Update geocode cache")
        _set_sync_error(None)
    except GitHubStoreError as exc:
        _set_sync_error(str(exc))


def hydrate_all_app_data(aggregates_path: Path, geocode_path: Path) -> bool:
    changed = hydrate_local_store(aggregates_path)
    if hydrate_geocode_cache(geocode_path):
        changed = True
    return changed
