"""
Test for 01-add-release-pipeline: the standalone (frozen) CLI loads the
`base` model shipped next to its executable when no --model-path is given,
and only then (specs/cli "Accept an explicit local model path").

Fakes sys.frozen / sys.executable instead of building a real frozen binary.

Run: python test_bundled_model_default.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

from transcriber import _bundled_model_path


def _fake_release_dir(tmp: str) -> str:
    """Lay out <tmp>/transcriber + <tmp>/model/model.bin like the CLI archive."""
    (Path(tmp) / "model").mkdir()
    (Path(tmp) / "model" / "model.bin").write_bytes(b"")
    return str(Path(tmp) / "transcriber")


def test_frozen_with_bundled_model_uses_it():
    with tempfile.TemporaryDirectory() as tmp:
        exe = _fake_release_dir(tmp)
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", exe):
            assert _bundled_model_path("base") == str(Path(tmp) / "model")
    print("OK: frozen CLI uses its bundled base model")


def test_other_model_size_ignores_bundled_model():
    with tempfile.TemporaryDirectory() as tmp:
        exe = _fake_release_dir(tmp)
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", exe):
            assert _bundled_model_path("small") is None
    print("OK: --model small ignores the bundled model")


def test_frozen_without_model_dir_resolves_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", str(Path(tmp) / "transcriber")):
            assert _bundled_model_path("base") is None
    print("OK: frozen CLI with no model/ next to it resolves by name")


def test_not_frozen_ignores_bundled_model():
    with tempfile.TemporaryDirectory() as tmp:
        exe = _fake_release_dir(tmp)
        with mock.patch.object(sys, "executable", exe):
            assert not getattr(sys, "frozen", False)
            assert _bundled_model_path("base") is None
    print("OK: running from source never picks up a bundled model")


if __name__ == "__main__":
    test_frozen_with_bundled_model_uses_it()
    test_other_model_size_ignores_bundled_model()
    test_frozen_without_model_dir_resolves_by_name()
    test_not_frozen_ignores_bundled_model()
