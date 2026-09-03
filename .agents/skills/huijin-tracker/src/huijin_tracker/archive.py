from __future__ import annotations

import hashlib
from pathlib import Path


def archive_bytes(
    root: str | Path,
    *,
    source: str,
    external_id: str,
    content: bytes,
    suffix: str,
) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    safe_id = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in external_id)[:160]
    folder = Path(root) / source
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe_id}__{digest[:12]}.{suffix.lstrip('.')}"
    if not path.exists():
        path.write_bytes(content)
    return digest, str(path.resolve())
