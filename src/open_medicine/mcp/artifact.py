from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import zipfile
from pathlib import Path

_ENTRYPOINT = b"from open_medicine.mcp.server import main\nmain()\n"
_ALLOWED_SUFFIXES = frozenset({".py", ".json"})


def _runtime_files(source_root: Path) -> list[tuple[str, bytes]]:
    root = Path(source_root).resolve(strict=True)
    package = root / "open_medicine"
    if not package.is_dir():
        raise ValueError("source root must contain open_medicine")
    rows: list[tuple[str, bytes]] = []
    for candidate in sorted(package.rglob("*")):
        if candidate.is_symlink():
            raise ValueError("runtime source tree must not contain symlinks")
        if not candidate.is_file() or candidate.suffix not in _ALLOWED_SUFFIXES:
            continue
        rows.append((candidate.relative_to(root).as_posix(), candidate.read_bytes()))
    if not rows:
        raise ValueError("runtime source tree is empty")
    return rows


def runtime_tree_sha256(source_root: Path) -> str:
    manifest = [
        {"path": name, "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}
        for name, payload in _runtime_files(source_root)
    ]
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _zip_info(name: str, *, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    mode = stat.S_IFREG | (0o755 if executable else 0o644)
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_STORED
    return info


def build_deterministic_zipapp(source_root: Path, python_executable: Path,
                               output: Path) -> str:
    interpreter = Path(python_executable).absolute()
    if not interpreter.is_file():
        raise ValueError("Python interpreter is missing")
    archive = io.BytesIO()
    archive.write(f"#!{interpreter}\n".encode())
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(_zip_info("__main__.py"), _ENTRYPOINT)
        for name, payload in _runtime_files(source_root):
            bundle.writestr(_zip_info(name), payload)
    payload = archive.getvalue()
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        temporary.chmod(0o755)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(payload).hexdigest()
