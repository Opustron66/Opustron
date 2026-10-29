"""Restore an approved memory archive; never extract claims with a model."""

import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

FILES = {"claims.jsonl", "docs.jsonl", "pages.jsonl"}
MAX_DOWNLOAD = 32 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Snapshot redirects must use HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate(path: Path) -> None:
    rows = 0
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("Snapshot rows must be objects")
            if path.name == "claims.jsonl":
                from chronicle.schema import Claim

                Claim.model_validate(row)
            elif path.name == "docs.jsonl":
                if not all(isinstance(row.get(k), str) and row[k] for k in ("doc_id", "text")):
                    raise ValueError("Snapshot documents need doc_id and text")
            else:
                if row.get("kind") not in {"topic", "entity"} or not all(
                    isinstance(row.get(k), str) for k in ("page_id", "title", "content")
                ):
                    raise ValueError("Invalid snapshot page")
            rows += 1
    if path.name != "pages.jsonl" and not rows:
        raise ValueError("Snapshot claims and documents must not be empty")


def restore_snapshot(root: Path, url: str, digest: str) -> Path:
    """Download a bounded ZIP and verify its pinned SHA-256 before loading it.

    Existing state is never overwritten. Failure messages omit the URL (which
    may carry a private download token) and document contents.
    """
    if urlsplit(url).scheme != "https" or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
        raise ValueError("Set an HTTPS snapshot URL and its 64-character SHA-256")
    digest = digest.lower()
    root.mkdir(parents=True, exist_ok=True)
    target = root / ("snapshot-" + digest)
    try:
        if target.is_dir():
            for name in FILES:
                _validate(target / name)
            return target
        with tempfile.TemporaryDirectory(prefix="snapshot-download-", dir=root) as scratch:
            scratch = Path(scratch)
            archive = scratch / "state.zip"
            sha = hashlib.sha256()
            total = 0
            with build_opener(HTTPSRedirects()).open(url, timeout=30) as response, archive.open("wb") as out:
                while chunk := response.read(64 * 1024):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD:
                        raise ValueError("Snapshot download is too large")
                    sha.update(chunk)
                    out.write(chunk)
            if sha.hexdigest() != digest:
                raise ValueError("Snapshot checksum mismatch")
            stage = scratch / "state"
            stage.mkdir()
            with zipfile.ZipFile(archive) as zipped:
                entries = zipped.infolist()
                if len(entries) != len(FILES) or {e.filename for e in entries} != FILES:
                    raise ValueError("Archive must contain exactly the three JSONL files at its root")
                if sum(e.file_size for e in entries) > MAX_EXPANDED:
                    raise ValueError("Expanded snapshot is too large")
                for entry in entries:
                    # Fixed filenames; no extractall, paths, executables or SQLite sidecars.
                    with zipped.open(entry) as source, (stage / entry.filename).open("wb") as out:
                        shutil.copyfileobj(source, out, length=64 * 1024)
                    _validate(stage / entry.filename)
            stage.rename(target)
        return target
    except Exception:
        raise ValueError("Could not restore memory snapshot; check its URL, SHA-256 and JSONL ZIP format") from None
