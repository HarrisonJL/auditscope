"""
Deterministic tests for AuditScope using genlayer-test's Direct Mode.

Three layers, same structure as the sibling SolvencyOracle/QuoteKeeper
projects:

1. Registration tests - input validation, immutability.
2. Integration tests (real attest() calls, both web fetches and the LLM
   extraction mocked) - MATCH/MISMATCH verdicts, grounded/ungrounded
   claims, latest_verdict/is_covered bookkeeping.
3. Consensus-boundary tests via direct_vm.run_validator - the actual
   point of this contract: a leader that fabricates a claim not present
   in the report is rejected; a leader whose source hashes disagree with
   an independent fetch is rejected; comment-only whitespace differences
   are handled by the whitespace-only normalization.
"""

import json

import pytest

REPORT_URL = "https://example.com/audit-report"
AUDITED_URL = "https://example.com/audited-source"
DEPLOYED_URL = "https://example.com/deployed-source"


def _deploy(direct_vm, direct_deploy, owner):
    direct_vm.sender = owner
    return direct_deploy("contracts/auditscope.py")


def _mock_page(direct_vm, url, body):
    direct_vm.mock_web(url, {"method": "GET", "status": 200, "body": body})


def _mock_claim_llm(direct_vm, claim):
    direct_vm.mock_llm(
        "extracting a short, exact identifying phrase",
        json.dumps({"claim": claim}),
    )


def _register(scope, direct_vm, target_id="T1", claim="audited as of commit a1b2c3d", report_body=None):
    report_body = report_body or f"We audited the contract. This is {claim} completed on 2026-01-15."
    _mock_page(direct_vm, REPORT_URL, report_body)
    scope.register_target(target_id, "Example Vault", REPORT_URL, AUDITED_URL, DEPLOYED_URL)


# --- Registration -----------------------------------------------------------


def test_initial_state(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    assert scope.get_state() == {"target_count": 0, "attestation_count": 0}


def test_register_target_succeeds_and_is_readable(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    scope.register_target("T1", "Example Vault", REPORT_URL, AUDITED_URL, DEPLOYED_URL)

    t = scope.get_target("T1")
    assert t["name"] == "Example Vault"
    assert t["audit_report_url"] == REPORT_URL
    assert t["audited_source_url"] == AUDITED_URL
    assert t["deployed_source_url"] == DEPLOYED_URL

    assert scope.get_state()["target_count"] == 1
    assert scope.list_targets() == [{"target_id": "T1", "name": "Example Vault"}]
    assert scope.latest_verdict("T1") == "NONE"
    assert scope.is_covered("T1") is False


def test_register_target_rejects_duplicate_id(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    scope.register_target("T1", "Example Vault", REPORT_URL, AUDITED_URL, DEPLOYED_URL)
    with pytest.raises(Exception):
        scope.register_target("T1", "Example Vault 2", REPORT_URL, AUDITED_URL, DEPLOYED_URL)


def test_register_target_rejects_non_https_url(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    with pytest.raises(Exception):
        scope.register_target("T1", "Example Vault", "http://example.com/report", AUDITED_URL, DEPLOYED_URL)


# --- Integration: real attest() calls ---------------------------------------


def test_attest_match_when_sources_identical(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm)
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "def vault():\n    return 1\n")
    _mock_page(direct_vm, DEPLOYED_URL, "def vault():\n    return 1\n")
    scope.attest("T1")

    a = scope.get_attestation(0)
    assert a["verdict"] == "MATCH"
    assert a["grounded"] is True
    assert a["claimed_reference"] == "audited as of commit a1b2c3d"
    assert a["audited_hash"] == a["deployed_hash"]
    assert scope.latest_verdict("T1") == "MATCH"
    assert scope.is_covered("T1") is True


def test_attest_mismatch_when_sources_differ(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm)
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "def vault():\n    return 1\n")
    _mock_page(direct_vm, DEPLOYED_URL, "def vault():\n    return 2\n")
    scope.attest("T1")

    a = scope.get_attestation(0)
    assert a["verdict"] == "MISMATCH"
    assert a["audited_hash"] != a["deployed_hash"]
    assert scope.is_covered("T1") is False


def test_attest_ignores_pure_whitespace_differences(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm)
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "def vault():\n    return 1\n")
    _mock_page(direct_vm, DEPLOYED_URL, "def vault():\n\n    return 1\n\n")  # extra blank lines, trailing spaces
    scope.attest("T1")

    assert scope.get_attestation(0)["verdict"] == "MATCH"


def test_attest_ungrounded_when_report_has_no_clear_reference(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm, report_body="This document describes our review process in general terms.")
    _mock_claim_llm(direct_vm, None)
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    scope.attest("T1")

    a = scope.get_attestation(0)
    assert a["grounded"] is False
    assert a["claimed_reference"] == ""
    assert a["verdict"] == "MATCH"  # coverage check is independent of whether a claim was grounded


def test_attest_rejects_unknown_target(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    with pytest.raises(Exception):
        scope.attest("NOPE")


# --- Consensus boundary: proposer-prover equivalence, via run_validator ----


def test_validator_agrees_when_claim_is_grounded_and_hashes_match(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm)
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "def vault():\n    return 1\n")
    _mock_page(direct_vm, DEPLOYED_URL, "def vault():\n    return 1\n")
    scope.attest("T1")  # captures validator_fn

    direct_vm.clear_mocks()
    _mock_page(direct_vm, REPORT_URL, "We audited the contract. This is audited as of commit a1b2c3d completed on 2026-01-15.")
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "def vault():\n    return 1\n")
    _mock_page(direct_vm, DEPLOYED_URL, "def vault():\n    return 1\n")
    audited_hash = _sha256_normalized("def vault():\n    return 1\n")
    leader_result = json.dumps({
        "claim": "audited as of commit a1b2c3d",
        "audited_hash": audited_hash,
        "deployed_hash": audited_hash,
    })
    assert direct_vm.run_validator(leader_result=leader_result) is True


def test_validator_rejects_fabricated_claim_not_in_report(direct_vm, direct_deploy, direct_owner):
    # The actual point of "proposer-prover": a leader that invents a
    # plausible-sounding reference which never appears in the report text
    # must be rejected, not merely re-checked by asking another LLM if it
    # sounds reasonable.
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm)
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    scope.attest("T1")

    direct_vm.clear_mocks()
    _mock_page(direct_vm, REPORT_URL, "We audited the contract. This is audited as of commit a1b2c3d completed on 2026-01-15.")
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")

    audited_hash = _sha256_normalized("code")
    leader_result = json.dumps({
        "claim": "reviewed by TotallyRealAuditors Inc on a date never mentioned",  # fabricated, not in report text
        "audited_hash": audited_hash,
        "deployed_hash": audited_hash,
    })
    assert direct_vm.run_validator(leader_result=leader_result) is False


def test_validator_rejects_hash_mismatch_from_independent_fetch(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm)
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    scope.attest("T1")

    direct_vm.clear_mocks()
    _mock_page(direct_vm, REPORT_URL, "We audited the contract. This is audited as of commit a1b2c3d completed on 2026-01-15.")
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    _mock_claim_llm(direct_vm, "audited as of commit a1b2c3d")

    leader_result = json.dumps({
        "claim": "audited as of commit a1b2c3d",
        "audited_hash": "0" * 64,  # leader claims a hash that doesn't match what I independently compute
        "deployed_hash": "0" * 64,
    })
    assert direct_vm.run_validator(leader_result=leader_result) is False


def test_validator_agrees_when_leader_and_validator_both_find_no_claim(direct_vm, direct_deploy, direct_owner):
    scope = _deploy(direct_vm, direct_deploy, direct_owner)
    _register(scope, direct_vm, report_body="Generic review notes, no specific reference.")
    _mock_claim_llm(direct_vm, None)
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    scope.attest("T1")

    direct_vm.clear_mocks()
    _mock_page(direct_vm, REPORT_URL, "Generic review notes, no specific reference.")
    _mock_page(direct_vm, AUDITED_URL, "code")
    _mock_page(direct_vm, DEPLOYED_URL, "code")
    _mock_claim_llm(direct_vm, None)

    audited_hash = _sha256_normalized("code")
    leader_result = json.dumps({"claim": None, "audited_hash": audited_hash, "deployed_hash": audited_hash})
    assert direct_vm.run_validator(leader_result=leader_result) is True


def _sha256_normalized(text: str) -> str:
    import hashlib
    lines = [line.strip() for line in text.splitlines()]
    normalized = "\n".join(line for line in lines if line)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
