from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.github_store import GitHubStoreError, download_bytes
from src.remote_json import (
    get_github_store_config,
    pull_json_file,
    push_json_dict,
    push_json_file,
    _set_sync_error,
)

# Re-export for app sidebar
from src.remote_json import (  # noqa: F401
    is_streamlit_cloud,
    last_sync_error,
    remote_store_enabled,
)


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
            push_store_snapshot(local)
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
        push_store_snapshot(local)
        _set_sync_error(None)
        return True

    _write_bytes(path, remote_bytes)
    _set_sync_error(None)
    return True


def push_store_snapshot(store: dict[str, Any]) -> None:
    from src.store_cache import store_to_json_bytes

    cfg = get_github_store_config()
    if not cfg:
        return
    push_json_file(
        cfg["path"],
        store_to_json_bytes(store),
        message="Update shipment aggregates",
    )


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

    remote_hit = pull_json_file(cfg["geocode_path"])

    from src.geocode import load_geocode_cache

    local = load_geocode_cache() if path.exists() else {}

    if remote_hit is None:
        if local:
            push_geocode_snapshot(local, cfg["geocode_path"])
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
        push_geocode_snapshot(merged, cfg["geocode_path"])
        return True
    return False


def push_geocode_snapshot(cache: dict[str, Any], geocode_path: str | None = None) -> None:
    cfg = get_github_store_config()
    if not cfg:
        return
    path = geocode_path or cfg["geocode_path"]
    push_json_dict(path, cache, message="Update geocode cache")


def hydrate_all_app_data(aggregates_path: Path, geocode_path: Path) -> bool:
    changed = hydrate_local_store(aggregates_path)
    if hydrate_geocode_cache(geocode_path):
        changed = True
    return changed
