import hashlib
import io
import json
import zipfile
from unittest.mock import Mock

import pytest

from chronicle.guard import state_snapshot
from chronicle.memory import MemoryAPI
from chronicle.schema import Claim


@pytest.fixture
def archive():
    claim = Claim(subject="Maya Patel", predicate="owns", object="billing service",
                  valid_from="2026-05-01", observed_at="2026-05-01", doc_id="demo-1",
                  quote="Maya Patel owns billing service.")
    return {"claims.jsonl": claim.model_dump_json() + "\n",
            "docs.jsonl": json.dumps({"doc_id": "demo-1", "date": "2026-05-01",
                                       "text": "Maya Patel owns billing service."}) + "\n",
            "pages.jsonl": ""}


def pack(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zipped:
        for name, text in files.items():
            zipped.writestr(name, text)
    return out.getvalue()


def serve(monkeypatch, data):
    opener = Mock()
    opener.open.side_effect = lambda *args, **kwargs: io.BytesIO(data)
    monkeypatch.setattr(state_snapshot, "build_opener", lambda *args: opener)
    return opener


def test_restore_after_ephemeral_storage_loss_without_ingestion(tmp_path, archive, monkeypatch):
    data = pack(archive)
    opener = serve(monkeypatch, data)
    digest = hashlib.sha256(data).hexdigest()
    for root in (tmp_path / "first-boot", tmp_path / "replacement-instance"):
        target = state_snapshot.restore_snapshot(root, "https://files.example/state.zip", digest)
        with MemoryAPI.from_state(target) as memory:
            assert memory.facts()[0].subject == "Maya Patel"
        assert state_snapshot.restore_snapshot(root, "https://files.example/state.zip", digest) == target
    assert opener.open.call_count == 2  # existing validated directories can be reused


def test_checksum_mismatch_does_not_modify_existing_state(tmp_path, archive, monkeypatch):
    (tmp_path / "claims.jsonl").write_text("existing state")
    serve(monkeypatch, pack(archive))
    with pytest.raises(ValueError, match="Could not restore"):
        state_snapshot.restore_snapshot(tmp_path, "https://files.example/state.zip?token=private", "0" * 64)
    assert (tmp_path / "claims.jsonl").read_text() == "existing state"
    assert not list(tmp_path.glob("snapshot-*"))


@pytest.mark.parametrize("extra", ["../escape", "nested/docs.jsonl", ".env", "memory.sqlite3"])
def test_reject_unexpected_archive_paths(tmp_path, archive, monkeypatch, extra):
    data = pack({**archive, extra: "bad"})
    serve(monkeypatch, data)
    with pytest.raises(ValueError, match="Could not restore"):
        state_snapshot.restore_snapshot(tmp_path, "https://files.example/state.zip", hashlib.sha256(data).hexdigest())
    assert not list(tmp_path.glob("snapshot-*"))


@pytest.mark.parametrize("name,value", [("claims.jsonl", ""), ("docs.jsonl", "[]\n"),
                                        ("pages.jsonl", '{"kind":"invalid"}\n')])
def test_reject_invalid_jsonl_before_publishing(tmp_path, archive, monkeypatch, name, value):
    data = pack({**archive, name: value})
    serve(monkeypatch, data)
    with pytest.raises(ValueError, match="Could not restore"):
        state_snapshot.restore_snapshot(tmp_path, "https://files.example/state.zip", hashlib.sha256(data).hexdigest())
    assert not list(tmp_path.glob("snapshot-*"))


@pytest.mark.parametrize("setting", ["MAX_DOWNLOAD", "MAX_EXPANDED"])
def test_bound_download_and_expansion(tmp_path, archive, monkeypatch, setting):
    data = pack(archive)
    serve(monkeypatch, data)
    monkeypatch.setattr(state_snapshot, setting, 8)
    with pytest.raises(ValueError, match="Could not restore"):
        state_snapshot.restore_snapshot(tmp_path, "https://files.example/state.zip", hashlib.sha256(data).hexdigest())


def test_download_error_hides_private_url(tmp_path, monkeypatch):
    opener = Mock()
    opener.open.side_effect = OSError("https://files.example/state.zip?token=secret")
    monkeypatch.setattr(state_snapshot, "build_opener", lambda *args: opener)
    with pytest.raises(ValueError) as error:
        state_snapshot.restore_snapshot(tmp_path, "https://files.example/state.zip?token=secret", "0" * 64)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("url,digest", [("http://files.example/state.zip", "0" * 64),
                                       ("https://files.example/state.zip", "")])
def test_require_https_and_pinned_checksum(tmp_path, url, digest):
    with pytest.raises(ValueError, match="HTTPS snapshot URL"):
        state_snapshot.restore_snapshot(tmp_path, url, digest)


def test_redirect_cannot_downgrade_https():
    with pytest.raises(ValueError, match="HTTPS"):
        state_snapshot.HTTPSRedirects().redirect_request(None, None, 302, "", {}, "http://files.example/state.zip")
