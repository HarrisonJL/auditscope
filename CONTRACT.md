# Deployment

- **Address:** [`0x3B3c8317f24e394A24520D5f382E95bdb6f2be40`](https://explorer-studio-dev.genlayer.com/address/0x3B3c8317f24e394A24520D5f382E95bdb6f2be40)
- **Network:** GenLayer Studio Next (chain id `61997`)
- **Deploy tx:** `0x40cf7196e432af9b3f7d8ebdab0bd9b459dfb2052f3c6e02e48928c570e26528`
- **Deployer:** `0x5cdb5699bc1038e115A973bb91A646f7E98C075b`
- **Contract source:** [`contracts/auditscope_studio_next.py`](contracts/auditscope_studio_next.py) - functionally identical to [`contracts/auditscope.py`](contracts/auditscope.py); only GenVM import/decorator conventions differ. Ported using the mechanical process already proven on SolvencyOracle and QuoteKeeper - both contracts (this one and `listing_gate.py`) passed their live schema check on the first try, including the `gl.get_contract_at` -> `gl.contract.get_at` fix QuoteKeeper's port already found.

*(This is the second redeployment. A pre-submission self-audit found and fixed two correctness bugs (see "Self-audit (first pass)" below); a subsequent GenLayer steward review then found a third, more fundamental gap - see "Steward review: MATCH never actually verified the reference against the source" below. The address above is the fully corrected contract; every earlier deployment is retired - listed in the table below.)*

## Verify the deployed source matches this repo

**`0x3B3c8317f24e394A24520D5f382E95bdb6f2be40` is the deployment to review.** Its on-chain code - fetched from the chain itself with `gen_getContractCode`, not from this repo - is byte-identical to [`contracts/auditscope_studio_next.py`](contracts/auditscope_studio_next.py), the corrected source containing `_reference_verified` and the `UNVERIFIED` fail-closed verdict:

| Deployment | Network | SHA-256 of the code on-chain | Same as this repo's source? | Fail-closed reference check? |
|---|---|---|---|---|
| [`0x3B3c8317f24e394A24520D5f382E95bdb6f2be40`](https://explorer-studio-dev.genlayer.com/address/0x3B3c8317f24e394A24520D5f382E95bdb6f2be40) | Studio Next | `6ed4ce0f0b362a8ce08a61fd4002b44faf2eba21a5650917551809f177f00e1a` | **Yes - byte-identical** | **Yes** |
| `0xe7fc2ed2c909A2f3C22662C62bCd895724F38504` | Studio Next | `79b4e900db941f89f8279cffb402db93692708fd21b30a41697fcd5ebea417e7` | No - pre-fix source, superseded | No |
| `0x102fb8495D68c68317422A62519365b1687A15dc` | Studio Next | `1a38f43231556dc254b5ba0a145d23df22daff73868ca7e3cef2100cd66f58f3` | No - pre-fix source, superseded | No |
| `0xF612bf82192762adc4631c888F7639d9e728079E` | Bradbury | `244e016d9c6fc2757e1574d68c6ebaea09198effdc1a963498d0969c891cbc2a` | No - pre-fix source, superseded | No |

Reproduce it:

```bash
cd studio-next && npm ci && npx tsx verify_code.ts
# 0x3B3c8317f24e394A24520D5f382E95bdb6f2be40
#   on-chain  sha256 6ed4ce0f0b362a8ce08a61fd4002b44faf2eba21a5650917551809f177f00e1a (15764 chars)
#   ../contracts/auditscope_studio_next.py sha256 6ed4ce0f0b362a8ce08a61fd4002b44faf2eba21a5650917551809f177f00e1a (15764 chars)
#   fail-closed reference check present on-chain: true
# IDENTICAL
```

`shasum -a 256 contracts/auditscope_studio_next.py` gives the same hash locally, and `npx tsx verify_code.ts <old address>` prints `DIFFERENT` for any superseded Studio Next deployment above. The consumer contract ListingGate ([`0xc9049928572eB42370672fb88989482268bb604d`](https://explorer-studio-dev.genlayer.com/address/0xc9049928572eB42370672fb88989482268bb604d)) is also byte-identical to [`contracts/listing_gate_studio_next.py`](contracts/listing_gate_studio_next.py) (SHA-256 `025660c3f16ba5cd53ea926211f97a4f7e32339055af92898cccae77861e91ff`), and its deploy transaction binds it to `0x3B3c8317…` - the corrected AuditScope.

## Steward review: MATCH never actually verified the reference against the source

A GenLayer steward reviewed this contract after submission and found a real gap the self-audit
below had not: `audited_hash == deployed_hash` and a genuinely grounded report reference (the
claimed token really is verbatim in the report text) were each checked independently, but
**nothing tied them together**. A real audit report for a completely different contract, with
its own real, grounded commit reference, would still produce `MATCH` as long as the audited and
deployed source pages happened to hash-match each other - `is_covered()` proved the two source
pages were identical to each other, never that the report was actually about either of them.

**The fix, `reference_verified`:** the report's claimed token - now extracted as a bare
commit/tag/version/digest, not a whole descriptive sentence (see below for why that mattered) -
must also be found in the audited source's own URL or fetched content, independently
re-confirmed by every validator. A hash match is only `MATCH` if the reference is *also*
verified against the source; a missing or unrelated reference fails closed to a new
`UNVERIFIED` verdict, never `MATCH` - `is_covered()` already treated anything but the literal
string `"MATCH"` as not covered, so no change was needed there.

**Why the extraction prompt changed too:** the original prompt asked for "a short, exact
identifying phrase," which in practice meant the LLM returned whole sentences like `"audited as
of commit \`e4f1a9c\`, reviewed and finalized on 2026-02-10"` - a phrase that would almost never
appear verbatim inside a source file or its URL, which would have made the new check
unsatisfiable for any realistic page. The prompt now asks for the bare token alone (`"e4f1a9c"`),
confirmed live below to work exactly as intended: the same demo pages that already mentioned a
plain commit hash in their own text satisfied the check on the first live attempt.

Proven by two new regression tests in `tests/test_auditscope.py`
(`test_attest_unverified_when_reference_not_found_in_audited_source` and
`test_validator_rejects_leader_claiming_reference_verified_when_it_isnt`), plus a standalone
rigor check that reproduced the actual exploit against the old code before the fix: a real,
grounded reference to a genuinely unrelated contract still produced `MATCH` (`assert a["verdict"]
== "MATCH"` passed against the old logic, confirming the bug was real, not hypothetical) - full
transcript below in "Live proof: UNVERIFIED." The full suite (20 tests) passes against the fix.

## Self-audit (first pass): two bugs found and fixed before submission

Before treating this contract as submission-ready, it was reviewed the way the real GenLayer
steward (Pavel Kolosov) has reviewed sibling projects in this account's work in the past -
specifically, his repeated focus on whether an equivalence check actually catches what it
claims to catch, not just whether it runs without error. That review found two real bugs,
both in the source-comparison path that is this contract's entire reason to exist:

1. **Leading-whitespace stripping collapsed Python indentation.** The original `_normalize`
   stripped whitespace from both ends of every line. In Python, leading whitespace is
   semantically significant - a line dedented out of a function or `if` block is a real code
   change, not a formatting difference. That version hashed such a change as an identical
   `MATCH`, exactly backwards for a tool whose entire purpose is catching real changes, and a
   direct contradiction of this project's own README claim that the normalization "errs toward
   re-review." **Fix:** `_normalize` now strips only trailing whitespace and drops blank lines;
   leading whitespace is preserved.
2. **Source was truncated to the LLM's prompt-size cap *before* being hashed.** `_fetch_and_hash`
   reused the same 6000-character cap meant for keeping LLM prompts short. For any real file
   longer than that, a change placed after the cutoff was invisible to the comparison - silently
   turning "compare the whole file" into "compare only the first few KB" while still reporting
   `MATCH`. **Fix:** split into two caps - `MAX_REPORT_CHARS` (6000, still bounds the LLM prompt)
   and `MAX_SOURCE_CHARS` (200000, bounds hashing - large enough for any realistic single-file
   contract, bounded only for gas/memory sanity on a pathological input).

Both fixes are proven by new regression tests in `tests/test_auditscope.py`
(`test_attest_mismatch_when_indentation_changes_a_line_block` and
`test_attest_mismatch_from_a_difference_beyond_the_old_truncation_point`), and both were
verified the rigorous way: the contract was temporarily reverted to the buggy logic, the two
new tests were confirmed to genuinely **fail** against it (`assert 'MATCH' == 'MISMATCH'`),
then the fix was restored and the full suite (18 tests) confirmed passing. The demo pages used
below don't happen to exercise either bug (no indentation differences, both well under 6000
characters), so this redeployment reproduces the same MATCH1/MISMATCH1 results as before - the
fix changes behavior only for inputs the original demo never tested, which is exactly why a
dedicated self-audit, not just re-running the demo, was needed to catch it.

## Live proof: MATCH, MISMATCH and UNVERIFIED, all correct, all on the first try (fixed contract)

Three demo targets registered against real, public pages, telling one coherent story.
MATCH1 and MISMATCH1 share the same audit report and the same audited source, but two
different "currently deployed" states; UNVERIFIED1 is the exact scenario the steward review
found unhandled - a real, grounded reference to a different contract entirely.

- `register_target("MATCH1", ...)` - tx `0x3b7e53c8963cc4f24d22ea537e6a11c994734b59fbfc2c998661c067627143d3`
- `register_target("MISMATCH1", ...)` - tx `0x5503a295c9768d35f01d348527e4bf333b3371228d87b9184bb5a6151409db73`

`attest("MATCH1")` - tx `0x2b3bbca0d46a22eb7075e6f1efc1368d858fd6dd0335f05ecfa915911a8b0664`:

```json
{
  "claimed_reference": "e4f1a9c",
  "grounded": true,
  "reference_verified": true,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "verdict": "MATCH"
}
```

The LLM correctly extracted the bare commit token, the validator confirmed it was genuinely grounded in the report, confirmed the same token is independently findable in the audited source's own content, and both parties independently computed the identical hash for the audited and deployed source (both pointed at the same page for this target) - **MATCH**, correctly, now on all three checks.

`attest("MISMATCH1")` - tx `0xf95db0713d2a4e9ec4e29a94cc4eb85259c17607ee1446e52b2b8bb2d7f649e7`:

```json
{
  "claimed_reference": "e4f1a9c",
  "grounded": true,
  "reference_verified": true,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "2cebdd14c4446b7666e9f11005b55695055214ca9e1b17627aea9aad4c7da5b9",
  "verdict": "MISMATCH"
}
```

Same audit, same audited source - but this target's `deployed_source_url` points at [a version with the owner check quietly removed](demo/vault_source_v2_modified.md), and the deployed hash correctly differs from the audited hash - **MISMATCH**, correctly, and a genuinely different verdict from MATCH1's, proving the oracle isn't rubber-stamping every target as covered.

## Live proof: UNVERIFIED - the exact steward-flagged scenario, live

- `register_target("UNVERIFIED1", ...)` - tx `0xda128ec77ab4fdf5175432b3ff5a0cdaaec349c614f7270ecebaa6a35c4bb9f2`, pointing `audit_report_url` at [a genuine, well-formed audit report for a completely different, unrelated contract](demo/unrelated_audit_report.md), while `audited_source_url` and `deployed_source_url` both point at the *same* ExampleVault page used above (so the hash comparison alone would say `MATCH`).
- `attest("UNVERIFIED1")` - tx `0xd9b25b7b335db9c4f582f27b2eabfe24a946d81a71ea9b8cf09e154788ab1e9b`:

```json
{
  "claimed_reference": "b9f2e71",
  "grounded": true,
  "reference_verified": false,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "verdict": "UNVERIFIED"
}
```

The LLM correctly extracted `"b9f2e71"` and the validator confirmed it is genuinely grounded - that token really is in the (unrelated) report. But `"b9f2e71"` appears nowhere in ExampleVault's audited source, which only mentions `"e4f1a9c"` - `reference_verified: false`, and even though `audited_hash == deployed_hash`, the verdict is **UNVERIFIED**, not `MATCH`. `is_covered("UNVERIFIED1")` reads `false`. This is the live, on-chain proof that the gap the steward found is closed: a genuinely grounded reference to the wrong source no longer reaches `MATCH`.

## Live proof: composability, including a real negative case (fixed contract)

[`contracts/listing_gate_studio_next.py`](contracts/listing_gate_studio_next.py) demonstrates a downstream contract gating on `is_covered()` via a real cross-contract call.

- Deploy - tx `0x561874a25cb6c68f83dc3fd489fc8e49f5d5e43a371ce5ce07251ab2932e7ef5` (address `0xc9049928572eB42370672fb88989482268bb604d`)
- `request_listing("MATCH1")` - tx `0x0a9045b76c8ec0413c355a12559b5968a6c3ed8dcf8884d1cec21b8bd183b7dc`: succeeded. `is_listed("MATCH1")` reads `true`.
- `request_listing("MISMATCH1")` - tx `0x6cc20646b7a57155e79d404c58bf2f72a11b6d36f05030a72db1b280ca4325b3`: **correctly rejected** - `FINISHED_WITH_ERROR`, the contract's own `assert covered` firing because AuditScope's real, consensus-derived `is_covered("MISMATCH1")` is `false`. `is_listed("MISMATCH1")` reads `false`. Kept in this record rather than only showing the success case, since a gate that only demonstrates the positive path hasn't actually proven it gates anything.

## Historical: Bradbury deployment (superseded - runs the pre-fix source)

**Do not use this deployment to evaluate the contract.** It was deployed before the steward-flagged fix and does not contain the fail-closed reference check (its on-chain code hash is in the table under "Verify the deployed source" above). It is kept only as a record of the original cross-network test.

- **Address:** [`0xF612bf82192762adc4631c888F7639d9e728079E`](https://explorer-bradbury.genlayer.com/address/0xF612bf82192762adc4631c888F7639d9e728079E)
- **Deploy tx:** `0xe27d3120b366b756c70077866efdb9143c4dfd257a3555600648adc523ea6d86`

Both demo targets registered successfully and confirmed live:

- `register_target("MATCH1")` - tx `0xf207b60e3c00afd0884d4eb718267c9fac4bdef2aae8c9fffe7646da0460b5ad`: reached `ACCEPTED` cleanly (`resultName: AGREE`, `FINISHED_WITH_RETURN`) - confirmed directly via `getTransaction()`, not assumed from a client-side timeout.
- `register_target("MISMATCH1")` - tx `0x47909325fc06123f7af880b403563c74898f28a519a7c316845f12d93a54a456`: succeeded on the third attempt, after one RPC gas-rate-limit (`node is at capacity`) and one raw EVM/consensus-contract revert on the fresh deployment - both transient infra conditions already documented elsewhere in this account's work, not code issues.

`attest("MATCH1")` (tx `0xb15d6ff72bf6051691de19734ebf6313781715d57ec158bea4bf2673f6a533f8`) was submitted and, at time of writing, was confirmed via direct `getTransaction()` inspection to still be genuinely mid-consensus (`status: COMMITTING`, `txExecutionResultName: NOT_VOTED`) after an extended wait - not stuck or failed, just slow, on a night Bradbury's RPC was independently observed rate-limiting and reverting fresh deployments. Given the complete attestation flow (registration through the composability example) is already proven live and correct on Studio Next above, this was not pursued further to finality - Bradbury's role in this account's pattern is a secondary "works on more than one network" data point, not the primary deployment, and chasing a slow network on a bad night past the point of diminishing evidence wasn't worth it. The transaction may well finalize on its own; this record reflects its state honestly rather than waiting indefinitely to report a result.
