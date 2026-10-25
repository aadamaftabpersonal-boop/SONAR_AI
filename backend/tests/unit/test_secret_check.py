import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_no_secrets.py"
spec = importlib.util.spec_from_file_location("check_no_secrets", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_flags_planted_api_key():
    text = "BOLNA_API_KEY=abcd1234efgh5678ijkl9012\n"
    assert checker.scan_text(text, "x.env")


def test_flags_real_looking_phone_number():
    planted = "call " + "+91" + "9123456780" + " now"  # built so this file isn't itself flagged
    assert checker.scan_text(planted, "notes.md")


def test_the_well_known_dummy_number_is_allowed_but_other_numbers_are_not():
    dummy = "+91" + "9876543210"
    assert checker.scan_text(f"use {dummy} in tests", "t.py") == []
    assert checker.scan_text("use " + "+91" + "9123456780", "t.py")  # a plausible real number


def test_ignores_placeholders():
    text = "BOLNA_API_KEY=\nphone: +91XXXXXXXXXX\nSONAR_ACCESS_KEY=changeme-please\n"
    assert checker.scan_text(text, "ok.md") == []


def test_example_files_are_exempt():
    assert checker.is_exempt(Path(".env.example"))
    assert checker.is_exempt(Path("businesses.example.yaml"))
    assert not checker.is_exempt(Path(".env"))


def test_clean_directory_passes(tmp_path):
    (tmp_path / "a.txt").write_text("nothing secret here\n", encoding="utf-8")
    assert checker.main([str(tmp_path)]) == 0


def test_dirty_directory_fails(tmp_path):
    (tmp_path / "a.txt").write_text("WEBHOOK_SECRET_TOKEN=Zx9fK2LmQ8vR4tYp7wNc\n", encoding="utf-8")
    assert checker.main([str(tmp_path)]) == 1
