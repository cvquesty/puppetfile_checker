"""Tests for check_puppetfile. The Forge is stubbed. No network."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "check_puppetfile"


def load_checker():
    loader = importlib.machinery.SourceFileLoader("check_puppetfile", str(SCRIPT))
    spec = importlib.util.spec_from_loader("check_puppetfile", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


CP = load_checker()


def test_same_release_ignores_spelling():
    assert CP.same_release("8.1.0", "8.1.0")
    assert CP.same_release("8.1.0", "v8.1.0")
    assert CP.same_release("1.0", "1.0.0")
    assert CP.same_release("6.0.0+build", "6.0.0")
    assert not CP.same_release("8.1.0", "8.2.0")
    assert not CP.same_release("6.0.0", "6.0.0-0-3")
    assert CP.version_numbers("nope") is None


def test_needs_update_rejects_a_matching_pin_marked_update():
    assert CP.needs_update("5.0.0", "6.0.0", "update")
    assert not CP.needs_update("1.0.6", "1.0.6", "current")
    assert not CP.needs_update("1.0", "1.0.0", "update")
    assert not CP.needs_update("1.0.0", None, "lookup failed")


def test_classify_same_release_is_current():
    assert CP.classify("1.0", "1.0.0", None)[2] == "current"
    assert CP.classify("5.0.0", "6.0.0", None)[2] == "update"
    assert CP.classify("9.0.0", "8.0.0", None)[2] == "current"
    assert CP.classify("1.0.0", None, "timed out")[2] == "timed out"


def test_accepted_version_skips_deleted_and_non_versions():
    payload = {
        "slug": "example-widget",
        "current_release": {
            "slug": "example-widget-6.0.0",
            "version": "6.0.0",
            "deleted_at": "2020-01-01",
        },
        "releases": [
            {
                "slug": "example-widget-6.0.0",
                "version": "6.0.0",
                "deleted_at": "2020-01-01",
            },
            {
                "slug": "example-widget-5.0.0",
                "version": "5.0.0",
                "deleted_at": None,
            },
        ],
    }
    assert CP.accepted_version("example-widget", payload) == "5.0.0"
    payload["current_release"]["deleted_at"] = None
    assert CP.accepted_version("example-widget", payload) == "6.0.0"
    payload["current_release"]["version"] = "latest"
    assert CP.accepted_version("example-widget", payload) == "5.0.0"


def test_parse_skips_git_and_keeps_quoted_pins():
    text = """\
mod 'example-one', '1.2.3'  # keep
mod "example-two", "4.0.0"
mod 'site',
  :git => 'git@github.com:example/site.git'
"""
    forge, git = CP.parse_puppetfile(text)
    assert forge == [("example-one", "1.2.3"), ("example-two", "4.0.0")]
    assert git == ["site"]


def test_rewrite_changes_only_the_behind_pin():
    text = "mod 'example-one', '1.0.0'  # note\nmod 'site',\n"
    updated, count = CP.rewrite_puppetfile(text, {"example-one": "1.1.0"})
    assert count == 1
    assert "mod 'example-one', '1.1.0'  # note\n" in updated
    assert "mod 'site',\n" in updated


def test_report_omits_a_pin_that_matches(capsys):
    resolved = [
        ("example-behind", "1.0.0", "1.1.0", "update"),
        ("example-same", "2.0.0", "2.0.0", "current"),
        ("example-spelled", "1.0", "1.0.0", "update"),
        ("example-down", "1.0.0", None, "lookup failed"),
    ]
    CP.print_report(Path("Puppetfile"), ["site"], resolved)
    out = capsys.readouterr().out
    assert "example-behind" in out
    assert "1.1.0" in out
    assert "example-same" not in out
    assert "example-spelled" not in out
    assert "1 module(s) should be updated." in out
    assert "1 module(s) could not be resolved." in out
    assert "Skipped git modules (no Forge version): site" in out


def test_main_lists_only_the_newer_forge_release(tmp_path, monkeypatch, capsys):
    puppetfile = tmp_path / "Puppetfile"
    puppetfile.write_text(
        "mod 'example-behind', '1.0.0'\nmod 'example-same', '2.0.0'\n",
        encoding="utf-8",
    )
    answers = {
        "example-behind": ("1.2.0", None),
        "example-same": ("2.0.0", None),
    }
    monkeypatch.setattr(CP, "fetch_current", lambda slug, timeout: answers[slug])
    status = CP.main([str(puppetfile)])
    out = capsys.readouterr().out
    assert status == 1
    assert "example-behind" in out
    assert "example-same" not in out
    assert "Puppetfile was not changed." in out
    assert puppetfile.read_text(encoding="utf-8").count("1.0.0") == 1


def test_main_refuses_to_write_without_the_word_update(tmp_path, monkeypatch, capsys):
    puppetfile = tmp_path / "Puppetfile"
    puppetfile.write_text("mod 'example-behind', '1.0.0'\n", encoding="utf-8")
    monkeypatch.setattr(CP, "fetch_current", lambda slug, timeout: ("1.2.0", None))
    monkeypatch.setattr("sys.stdin", type("In", (), {"isatty": lambda self: True, "readline": lambda self: "no\n"})())
    status = CP.main([str(puppetfile), "-f"])
    assert status == 2
    assert puppetfile.read_text(encoding="utf-8") == "mod 'example-behind', '1.0.0'\n"
    assert "Cancelled" in capsys.readouterr().out


def test_main_writes_after_the_word_update(tmp_path, monkeypatch, capsys):
    puppetfile = tmp_path / "Puppetfile"
    puppetfile.write_text("mod 'example-behind', '1.0.0'\n", encoding="utf-8")
    monkeypatch.setattr(CP, "fetch_current", lambda slug, timeout: ("1.2.0", None))
    monkeypatch.setattr(
        "sys.stdin",
        type("In", (), {"isatty": lambda self: True, "readline": lambda self: "update\n"})(),
    )
    # 1 means the file was behind and has now been rewritten.
    assert CP.main([str(puppetfile), "-f"]) == 1
    assert puppetfile.read_text(encoding="utf-8") == "mod 'example-behind', '1.2.0'\n"
    assert list((tmp_path / "changes").glob("Puppetfile.*"))
    capsys.readouterr()


def test_backup_keeps_five_copies(tmp_path, monkeypatch):
    puppetfile = tmp_path / "Puppetfile"
    puppetfile.write_text("mod 'example-behind', '1.0.0'\n", encoding="utf-8")
    stamps = iter(f"20260101-00000{n}" for n in range(6))

    class Clock:
        @staticmethod
        def now():
            stamp = next(stamps)
            return type("N", (), {"strftime": lambda self, fmt, stamp=stamp: stamp})()

    monkeypatch.setattr(CP, "datetime", Clock)
    for _ in range(6):
        CP.backup_puppetfile(puppetfile)
    backups = list((tmp_path / "changes").glob("Puppetfile.*"))
    assert len(backups) == 5
    names = sorted(path.name for path in backups)
    assert "Puppetfile.20260101-000000" not in names


def test_fetch_current_uses_the_stubbed_body(monkeypatch):
    payload = {
        "slug": "example-widget",
        "current_release": {
            "slug": "example-widget-3.0.0",
            "version": "3.0.0",
            "deleted_at": None,
        },
    }
    body = json.dumps(payload).encode("utf-8")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return body

    monkeypatch.setattr(CP.urllib.request, "urlopen", lambda request, timeout: Response())
    version, error = CP.fetch_current("example-widget", 5)
    assert version == "3.0.0"
    assert error is None


def test_missing_puppetfile_exits_2(tmp_path, capsys):
    status = CP.main([str(tmp_path / "missing")])
    assert status == 2
    assert "cannot read" in capsys.readouterr().err
