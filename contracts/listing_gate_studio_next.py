# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

# ListingGate - a minimal example of composing with AuditScope: only
# allows a target to be marked "listed" if AuditScope currently reports
# its deployed source matches what was audited. Demonstrates that
# is_covered() is a real primitive another contract can gate on, not
# just a display value.
# Header must end in a blank line (real GenVM requirement).

import genlayer as gl
from genlayer.types import *
from genlayer.storage import TreeMap, DynArray
from dataclasses import dataclass
import datetime

MAX_TARGET_ID_LEN = 32


def _now() -> datetime.datetime:
    return datetime.datetime.fromisoformat(gl.message.datetime)


@gl.storage.allow
@dataclass
class Listing:
    listed: bool
    listed_at: datetime.datetime
    listed_by: Address


class ListingGate(gl.contract.Contract):
    auditscope_address: Address
    listings: TreeMap[str, Listing]

    # Address taken as a hex string, not Address, purely so callers don't
    # need an SDK-specific Address type in scope - converted once, here.
    def __init__(self, auditscope_address: str) -> None:
        self.auditscope_address = Address(auditscope_address)

    # Permissionless - any keeper can (re-)check a target's status.
    # Deterministic: this contract makes no nondet call of its own, it
    # only reads a decision AuditScope's own validator committee already
    # reached.
    @gl.public.write
    def request_listing(self, target_id: str) -> None:
        assert 1 <= len(target_id) <= MAX_TARGET_ID_LEN, f"target_id must be 1-{MAX_TARGET_ID_LEN} chars"
        scope = gl.contract.get_at(self.auditscope_address)
        covered = scope.view().is_covered(target_id)
        assert covered, "AuditScope does not currently report this target as covered"

        listing = self.listings.get_or_insert_default(target_id)
        listing.listed = True
        listing.listed_at = _now()
        listing.listed_by = gl.message.sender_address

    # Explicit revocation, since AuditScope's verdict can change (a later
    # attest() could report MISMATCH after a listing was granted) and
    # nothing currently re-checks existing listings automatically - a
    # real deployment would want this called whenever AuditScope emits a
    # new attestation for a listed target.
    @gl.public.write
    def revoke_listing(self, target_id: str) -> None:
        assert target_id in self.listings, "not listed"
        self.listings[target_id].listed = False

    @gl.public.view
    def is_listed(self, target_id: str) -> bool:
        if target_id not in self.listings:
            return False
        return self.listings[target_id].listed

    @gl.public.view
    def get_listing(self, target_id: str) -> dict:
        listing = self.listings[target_id]
        return {
            "listed": listing.listed,
            "listed_at": listing.listed_at.isoformat(),
            "listed_by": listing.listed_by.as_hex,
        }
