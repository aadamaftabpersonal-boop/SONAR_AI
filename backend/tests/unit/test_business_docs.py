"""The business documents must stay honest: no unsourced numbers, and the consent script must keep
its promises (AI disclosure, transcription, opt-out) and not promise anything unbuilt."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"

spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts" / "check_claims.py")
claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claims)

CASE = (DOCS / "BUSINESS_CASE.md").read_text(encoding="utf-8")
CONSENT = (DOCS / "CONSENT_SCRIPT.md").read_text(encoding="utf-8")
# markdown quote and bold markers and line wraps must not hide a phrase from the checks
FLAT_CONSENT = " ".join(re.sub(r"[>*]", " ", CONSENT.lower()).split())


# --- the lint itself -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "Conversion improved by 40%.",
        "The TAM is large.",
        "A multi-billion opportunity.",
        "It is a growing market.",
        "Revenue of 5 per query.",
        "Worth a crore.",
        "Market size is big.",
    ],
)
def test_lint_flags_unsourced_claims(line):
    assert claims.check_text(line), line


@pytest.mark.parametrize(
    "line",
    [
        "Ask about the last time it happened.",
        "At most 4 calls a day.",
        "6 of 10 shops said yes.",
        "Cost per useful result is measured.",
    ],
)
def test_lint_allows_plain_measured_statements(line):
    assert claims.check_text(line) == []


def test_marker_exempts_a_line_that_states_what_we_do_not_claim():
    assert claims.check_text("No 40% figure here. <!-- claim-ok -->") == []


def test_lint_reports_file_and_line():
    out = claims.check_text("ok\nbad 12% here", "x.md")
    assert out and out[0].startswith("x.md:2:")


@pytest.mark.parametrize("name", ["BUSINESS_CASE.md", "CONSENT_SCRIPT.md", "DISCOVERY_LOG.md"])
def test_the_business_documents_are_clean(name):
    path = DOCS / name
    assert claims.check_text(path.read_text(encoding="utf-8"), name) == []


def test_the_cli_returns_zero_on_the_real_documents():
    assert claims.main([]) == 0


# --- the business case -----------------------------------------------------------------------


def test_every_hypothesis_has_a_test_a_pass_rule_and_a_kill_rule():
    for h in ("H-1", "H-2", "H-3", "H-4", "H-5"):
        section = CASE.split(f"### {h}")[1].split("### H-")[0].split("\n## ")[0]
        for needed in ("Cheapest test", "Pass:", "Kill:", "Result:"):
            assert needed in section, f"{h} lacks {needed}"


def test_no_hypothesis_claims_a_result_it_does_not_have():
    assert CASE.count("_not run_") >= 5
    assert "Result:** passed" not in CASE


def test_the_business_case_says_nothing_is_measured():
    assert "nothing here is measured" in CASE.lower()


def test_the_ladder_does_not_overstate_what_is_built():
    row = next(line for line in CASE.splitlines() if line.startswith("| L1 "))
    assert "simulator" in row and "Not yet run against a real provider" in row
    for level in ("L3", "L4", "L5"):
        line = next(x for x in CASE.splitlines() if x.startswith(f"| {level} "))
        assert "Designed only" in line


# --- the consent script ----------------------------------------------------------------------


def test_the_script_is_versioned():
    assert "consent_script_v2" in CONSENT


def test_the_script_discloses_the_ai_the_transcription_and_the_opt_out():
    assert "ai assistant" in FLAT_CONSENT
    assert "transcribed" in FLAT_CONSENT
    assert "say stop at any time" in FLAT_CONSENT
    assert "we will not call again" in FLAT_CONSENT


def test_the_script_does_not_promise_the_digest_before_it_exists():
    assert "do not use this variant until the demand digest page works" in FLAT_CONSENT


def test_the_script_forbids_unbuilt_promises_and_false_partnerships():
    for phrase in (
        "we're partnered with",
        "you'll get more customers",
        "it's guaranteed",
    ):
        assert phrase in FLAT_CONSENT  # listed in the "what not to say" checklist


def test_the_script_does_not_claim_calls_are_unrecorded():
    assert "do not" in FLAT_CONSENT and "confirm this after spike s-9" in FLAT_CONSENT


def test_the_script_makes_no_compliance_claim():
    assert "does not make a compliance claim" in FLAT_CONSENT


def test_recording_fields_match_what_the_seed_loader_requires():
    for field in (
        "participation_status",
        "consent_recorded_at",
        "consent_note",
        "best_call_window",
    ):
        assert f"`{field}`" in CONSENT


def test_future_consent_fields_are_not_to_be_recorded_yet():
    assert "do not record them yet" in FLAT_CONSENT
