"""
Deterministic tests for ListingGate using genlayer-test's Direct Mode.

Direct Mode cannot simulate cross-contract calls without a "glsim" hook
this project doesn't configure (same limitation documented for the
sibling QuoteKeeper project's RetainerConsumer). That means
request_listing()'s actual read of AuditScope.is_covered() cannot be
unit tested here - it's verified live instead, once both contracts are
deployed (see CONTRACT.md). What's tested here is everything
request_listing() doesn't touch: constructor, revoke_listing, and
is_listed's default-false behavior.
"""

import pytest

AS_ADDRESS = "0x" + "11" * 20  # placeholder - never actually called in these tests


def _deploy(direct_vm, direct_deploy, owner):
    direct_vm.sender = owner
    return direct_deploy("contracts/listing_gate.py", AS_ADDRESS)


def test_is_listed_defaults_to_false(direct_vm, direct_deploy, direct_owner):
    gate = _deploy(direct_vm, direct_deploy, direct_owner)
    assert gate.is_listed("T1") is False


def test_revoke_listing_rejects_unlisted_target(direct_vm, direct_deploy, direct_owner):
    gate = _deploy(direct_vm, direct_deploy, direct_owner)
    with pytest.raises(Exception):
        gate.revoke_listing("T1")


def test_request_listing_is_unreachable_without_glsim(direct_vm, direct_deploy, direct_owner):
    # Documenting the gap explicitly rather than silently skipping it:
    # request_listing() calls gl.get_contract_at(...).view().is_covered(...)
    # unconditionally, before its own assert, so even this basic call
    # cannot run in Direct Mode without a glsim hook.
    gate = _deploy(direct_vm, direct_deploy, direct_owner)
    with pytest.raises(Exception):
        gate.request_listing("T1")
