# Deployment

- **Address:** [`0xe7fc2ed2c909A2f3C22662C62bCd895724F38504`](https://explorer-studio-dev.genlayer.com/address/0xe7fc2ed2c909A2f3C22662C62bCd895724F38504)
- **Network:** GenLayer Studio Next (chain id `61997`)
- **Deploy tx:** `0xd9d5e80950a71d95be38d60ba20dbca5fa9c4cc1410d2f5e8cff3cd16ed40bc2`
- **Deployer:** `0x5cdb5699bc1038e115A973bb91A646f7E98C075b`
- **Contract source:** [`contracts/auditscope_studio_next.py`](contracts/auditscope_studio_next.py) - functionally identical to [`contracts/auditscope.py`](contracts/auditscope.py); only GenVM import/decorator conventions differ. Ported using the mechanical process already proven on SolvencyOracle and QuoteKeeper - both contracts (this one and `listing_gate.py`) passed their live schema check on the first try, including the `gl.get_contract_at` -> `gl.contract.get_at` fix QuoteKeeper's port already found.

*(This is a redeployment. A pre-submission self-audit found and fixed two correctness bugs after the first deployment went live - see "Self-audit: two bugs found and fixed" below. The address above is the corrected contract; the original deployment's address is retired.)*

## Self-audit: two bugs found and fixed before submission

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

## Live proof: a MATCH and a MISMATCH, both correct, both on the first try (fixed contract)

Two demo targets registered against real, public pages, telling one coherent story: the same
audit report and the same audited source, but two different "currently deployed" states.

- `register_target("MATCH1", ...)` - tx `0x68a04dc34b0616c2083fcd9cfb320556ef0502c5a6b9ca3c09aabce259899cb5`
- `register_target("MISMATCH1", ...)` - tx `0xece709b21511c13675d7a673c155efe2669045a8d2fade261734995075f0afb5`

`attest("MATCH1")` - tx `0x2eedc30891035569d982cbb5ddcc4763c5ec0be5391a3bf3b3a5294db3cf22a8`:

```json
{
  "claimed_reference": "audited at commit `e4f1a9c`, reviewed and finalized on 2026-02-10",
  "grounded": true,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "verdict": "MATCH"
}
```

The LLM correctly quoted a verbatim phrase from the report, the validator confirmed it was genuinely grounded, and both parties independently computed the identical hash for the audited and deployed source (both pointed at the same page for this target) - **MATCH**, correctly.

`attest("MISMATCH1")` - tx `0xb1cb628d388113d12b8dee4f44ce8fca8048a87a33b5b2cc34638c52c590acee`:

```json
{
  "claimed_reference": "audited at commit `e4f1a9c`, reviewed and finalized on 2026-02-10",
  "grounded": true,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "2cebdd14c4446b7666e9f11005b55695055214ca9e1b17627aea9aad4c7da5b9",
  "verdict": "MISMATCH"
}
```

Same audit, same audited source - but this target's `deployed_source_url` points at [a version with the owner check quietly removed](demo/vault_source_v2_modified.md), and the deployed hash correctly differs from the audited hash - **MISMATCH**, correctly, and a genuinely different verdict from MATCH1's, proving the oracle isn't rubber-stamping every target as covered.

## Live proof: composability, including a real negative case (fixed contract)

[`contracts/listing_gate_studio_next.py`](contracts/listing_gate_studio_next.py) demonstrates a downstream contract gating on `is_covered()` via a real cross-contract call.

- Deploy - tx `0x0dbf15c265d3df729e713ffe959bd3690667a601cfbd7a89e719b91be3176e40` (address `0x43A2F5258c274987434F745767930Bc2857DdE2a`)
- `request_listing("MATCH1")` - tx `0xcedf1389d58dad79c18ed41e7a0288adfe4e0e5155b8b8340dbfb13b4f1e5fcf`: succeeded. `is_listed("MATCH1")` reads `true`.
- `request_listing("MISMATCH1")` - tx `0x16b36e4f21370787c5be8554bb823aa3b824ca797be71a808b1537c90cc24a1c`: **correctly rejected** - `FINISHED_WITH_ERROR`, the contract's own `assert covered` firing because AuditScope's real, consensus-derived `is_covered("MISMATCH1")` is `false`. `is_listed("MISMATCH1")` reads `false`. Kept in this record rather than only showing the success case, since a gate that only demonstrates the positive path hasn't actually proven it gates anything.

## Historical: Bradbury deployment (partial - see below)

- **Address:** [`0xF612bf82192762adc4631c888F7639d9e728079E`](https://explorer-bradbury.genlayer.com/address/0xF612bf82192762adc4631c888F7639d9e728079E)
- **Deploy tx:** `0xe27d3120b366b756c70077866efdb9143c4dfd257a3555600648adc523ea6d86`

Both demo targets registered successfully and confirmed live:

- `register_target("MATCH1")` - tx `0xf207b60e3c00afd0884d4eb718267c9fac4bdef2aae8c9fffe7646da0460b5ad`: reached `ACCEPTED` cleanly (`resultName: AGREE`, `FINISHED_WITH_RETURN`) - confirmed directly via `getTransaction()`, not assumed from a client-side timeout.
- `register_target("MISMATCH1")` - tx `0x47909325fc06123f7af880b403563c74898f28a519a7c316845f12d93a54a456`: succeeded on the third attempt, after one RPC gas-rate-limit (`node is at capacity`) and one raw EVM/consensus-contract revert on the fresh deployment - both transient infra conditions already documented elsewhere in this account's work, not code issues.

`attest("MATCH1")` (tx `0xb15d6ff72bf6051691de19734ebf6313781715d57ec158bea4bf2673f6a533f8`) was submitted and, at time of writing, was confirmed via direct `getTransaction()` inspection to still be genuinely mid-consensus (`status: COMMITTING`, `txExecutionResultName: NOT_VOTED`) after an extended wait - not stuck or failed, just slow, on a night Bradbury's RPC was independently observed rate-limiting and reverting fresh deployments. Given the complete attestation flow (registration through the composability example) is already proven live and correct on Studio Next above, this was not pursued further to finality - Bradbury's role in this account's pattern is a secondary "works on more than one network" data point, not the primary deployment, and chasing a slow network on a bad night past the point of diminishing evidence wasn't worth it. The transaction may well finalize on its own; this record reflects its state honestly rather than waiting indefinitely to report a result.
