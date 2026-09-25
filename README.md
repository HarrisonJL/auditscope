# AuditScope

A reusable audit-coverage attestor for [GenLayer](https://genlayer.com): register a deployed contract's audit report alongside its audited and currently-deployed source, and any wallet can trigger a real validator committee to independently verify whether the audit report's claims are genuinely grounded in its own text and whether what was actually audited still matches what's actually deployed - `MATCH` / `MISMATCH`, not a badge nobody re-checks.

**Live on GenLayer Studio Next. Testnet only.** (Also live, separately, on Bradbury - see [`CONTRACT.md`](CONTRACT.md).)

## The problem this solves

An audit badge gets treated as a permanent safety certificate, but an audit is a scoped review of specific code at a specific commit - not a guarantee about whatever gets deployed afterward. Code changes after an audit ships, sometimes by accident, sometimes because "just one more fix" felt too small to warrant a re-review. Nobody automatically re-checks that the deployed bytecode still matches what was actually reviewed. GenLayer's validator committee makes that check independently verifiable instead of something everyone just has to trust: multiple validators fetch the same audit report and source pages themselves, and only agree on a verdict if their independent readings actually hold up.

## How it works

`register_target(target_id, name, audit_report_url, audited_source_url, deployed_source_url)` - permissionless, and once registered, immutable. All three URLs are provided directly by the registrant - this contract doesn't try to parse a repo URL and commit hash out of the report to go fetch files itself, which would mean constructing URLs from LLM-extracted parts and trusting that construction was right. Point `audited_source_url` at the code as it was when reviewed, and `deployed_source_url` at what's actually live now (in principle, an explorer's verified-source page); the contract just compares them.

`attest(target_id)` - permissionless, runs two independent checks:

```python
def leader_fn() -> str:
    report_text = gl.nondet.web.render(report_url, mode="text")[:MAX_REPORT_CHARS]
    claim = _extract_claim(report_text)                 # LLM proposes a verbatim-quoted pointer
    audited_hash = _fetch_and_hash(audited_url)          # deterministic - no LLM, truncated only at MAX_SOURCE_CHARS
    deployed_hash = _fetch_and_hash(deployed_url)        # deterministic - no LLM, truncated only at MAX_SOURCE_CHARS
    return json.dumps({"claim": claim, "audited_hash": audited_hash, "deployed_hash": deployed_hash})

def validator_fn(leaders_res) -> bool:
    my_report_text = gl.nondet.web.render(report_url, mode="text")[:MAX_REPORT_CHARS]
    if leader_claim is not None and leader_claim not in my_report_text:
        return False                                     # fabricated - not actually in the report
    return leader_data["audited_hash"] == my_audited_hash and leader_data["deployed_hash"] == my_deployed_hash
```

`MAX_REPORT_CHARS` (6000) bounds what goes into the LLM prompt; `MAX_SOURCE_CHARS` (200000) separately bounds what gets hashed - see "Two different truncation caps" below for why reusing one small cap for both was a real bug, not just tidiness.

The stored verdict - `MATCH` if the audited and deployed source hash identically (after normalization), `MISMATCH` otherwise - is computed deterministically from the agreed-upon hashes, the same one-source-of-truth pattern as SolvencyOracle's `_compute_verdict` and QuoteKeeper's `_local_verdict`. `grounded` records separately whether the audit report actually contained a specific, verbatim-checkable reference (a commit hash, date, or similar) - useful evidence, but independent of whether the source itself matches.

## Design notes

**Proposer-prover equivalence: let the LLM point, let code prove.** SolvencyOracle and QuoteKeeper both compare two *independent* LLM extractions against each other (within tolerance, or on the decision they imply). AuditScope's report-grounding check is different: the leader's LLM extraction isn't compared against the validator's own LLM extraction at all - it's checked against *ground truth*, deterministically. A validator re-fetches the report itself and does a plain substring check: does the leader's claimed reference actually appear, verbatim, in the report text? An LLM that hallucinates a plausible-sounding but absent commit hash or date is caught by this exactly the same way a person fact-checking a citation would be - not by asking a second opinion whether the citation *sounds* plausible, but by going and looking. `tests/test_auditscope.py::test_validator_rejects_fabricated_claim_not_in_report` proves exactly this: a leader claiming an invented auditor name that never appears in the report is rejected, even though the invented text is perfectly plausible-sounding on its own.

**Two checks, two different equivalence bars, on purpose.** The audited-vs-deployed source comparison is fully deterministic (same URLs, same normalization, every honest validator computes the identical hash) - the right bar is exact equality, like `strict_eq`. The report-grounding check has real LLM extraction variance (two validators might phrase or select a slightly different quoted span) - but grounding doesn't need the two LLM outputs to match each other, only for whichever one the leader picked to actually be real. That's a genuinely different question from "do our answers agree," which is why it needs its own check rather than reusing either SolvencyOracle's tolerance pattern or QuoteKeeper's decision-margin pattern.

**Trailing-whitespace normalization, not comment-stripping - and never leading whitespace.** `_normalize` strips trailing per-line whitespace and drops blank lines, nothing else. Leading whitespace is preserved deliberately: in Python, indentation is semantically significant, so a line dedented out of a function or `if` block is a real code change, not formatting noise. An earlier version of this function stripped leading whitespace too - a pre-submission self-audit caught that this let such a dedent hash identically to the original, reporting a false `MATCH` for what was actually a functional change (`tests/test_auditscope.py::test_attest_mismatch_when_indentation_changes_a_line_block` is the regression test, and it was confirmed to genuinely fail against the old code before the fix). A change that's *only* a comment or pure reformatting edit will still read as `MISMATCH` here - for a tool whose whole point is flagging "the deployed code isn't what was reviewed," erring toward re-review is the safe default, even though it means some genuinely harmless diffs get flagged too.

**Two different truncation caps, because they bound two genuinely different things.** `MAX_REPORT_CHARS` (6000) bounds what gets fed into the LLM prompt - a real cost/context concern. `MAX_SOURCE_CHARS` (200000) separately bounds what gets hashed - plain hashing has no such concern, so this cap is generously large, bounded only for gas/memory sanity on a pathological input. These used to be the same small constant. The same pre-submission self-audit that found the indentation bug also caught that reusing one small cap for both meant source got truncated *before* hashing - for any real file longer than 6000 characters, a change placed after that cutoff was invisible to the comparison, silently turning "compare the whole file" into "compare only the first few KB" while still reporting `MATCH`. `tests/test_auditscope.py::test_attest_mismatch_from_a_difference_beyond_the_old_truncation_point` is the regression test.

**`claimed_reference` is supplementary evidence, not a consensus gate on its own.** An attestation can still reach a `MATCH`/`MISMATCH` verdict even when no clear reference was groundable in the report (both leader and validator agreeing "nothing specific found" is itself a valid, if weaker, outcome) - the source-hash comparison is the core claim this contract makes; the grounded reference is corroborating context for a human reading the attestation, not something that blocks the coverage check.

**Immutable registration**, same reasoning as every other attestor in this account's work: a target's URLs never change after registration, so a historical attestation's context can't be quietly altered out from under it.

## Verified platform facts

This contract exists in two source files: [`contracts/auditscope.py`](contracts/auditscope.py)
(Bradbury, GenVM v0.2.11, test-covered by the suite below) and a Studio Next variant (a
newer GenVM generation - the primary live deployment, ported using the mechanical process
documented in the sibling [SolvencyOracle](https://github.com/HarrisonJL/solvency-oracle)
and [QuoteKeeper](https://github.com/HarrisonJL/quotekeeper) projects' `studio-next/README.md`
files, including the `gl.get_contract_at` -> `gl.contract.get_at` move QuoteKeeper's port
already found for [`contracts/listing_gate.py`](contracts/listing_gate.py)).

Direct Mode cannot simulate cross-contract calls without a "glsim" hook this project
doesn't configure (same limitation as QuoteKeeper's `RetainerConsumer`). `listing_gate.py`'s
`request_listing()`, which makes exactly one such call, is verified live only - see
CONTRACT.md.

## Testing

`tests/test_auditscope.py` (18 tests) and `tests/test_listing_gate.py` (3 tests),
`genlayer-test` Direct Mode:

1. **Registration** - input validation, immutability.
2. **Integration** (real `attest()` calls, both web fetches and the LLM extraction mocked) - `MATCH`/`MISMATCH` verdicts, trailing-whitespace/blank-line differences correctly ignored, ungrounded-claim bookkeeping, `latest_verdict`/`is_covered`.
3. **Consensus-boundary tests** via `direct_vm.run_validator(leader_result=...)` - the actual point of this contract: a fabricated claim not present in an independently-fetched report is rejected; a claimed source hash that doesn't match an independent fetch is rejected; leader and validator both finding no groundable claim is a valid agreement.
4. **Self-audit regressions** - an indentation change that dedents a line out of its block is correctly caught as `MISMATCH` (not masked by over-eager whitespace stripping); a change placed beyond the old 6000-character truncation point is correctly caught as `MISMATCH` (not hidden by truncating source before hashing it). Both were confirmed to genuinely fail against the pre-fix code before being confirmed to pass against the fix - see "Design notes."
5. `test_listing_gate.py` covers everything `request_listing()`'s untestable cross-contract call doesn't touch, and documents, with a passing test, exactly why that call can't run in Direct Mode.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install genlayer-py==0.16.3 genlayer-test==0.29.2 pytest==9.1.1 genvm-linter==0.11.0
genvm-lint check contracts/auditscope.py
genvm-lint check contracts/listing_gate.py
python -m pytest tests/ -v
```

## Deployment

See [`CONTRACT.md`](CONTRACT.md) for live addresses, deploy transactions, and a real
end-to-end run: a `MATCH` attestation, a `MISMATCH` attestation (a demo vault whose owner
check was quietly removed after audit - exactly the kind of gap this contract exists to
catch), and `ListingGate` granting and reflecting a real listing decision against the
live `is_covered` result.

## Known limitations

- **Testnet only.**
- **URLs are provided directly, not extracted from the report.** A more automated v2 could parse `{repo_url, commit_sha, in_scope_paths}` from the report and reconstruct fetch URLs itself - deliberately not attempted here, since that shifts real integration fragility (URL construction, GitHub-specific assumptions, variable-length scope) onto the exact mechanism meant to be trustworthy. Direct URLs mean a human (or an upstream process) vouches for what "audited" and "deployed" actually point to; this contract's job is checking whether those two things, once pointed to, actually match - not discovering them.
- **Whole-page comparison, not per-function coverage.** A single-byte difference anywhere produces the same `MISMATCH` as a complete rewrite - no partial-coverage percentage. A v2 tracking per-function hashes would need a real, language-aware source splitter, which is a meaningfully bigger undertaking than whitespace normalization.
- **Trailing-whitespace normalization only** - see "Design notes." Comment-only or pure-reformatting edits still read as `MISMATCH`, the deliberate conservative direction.
- **Source hashed up to 200,000 characters (`MAX_SOURCE_CHARS`)** - generous enough for any realistic single-file contract, but still a hard cap; a source file larger than that would have anything past the cutoff go uncompared. See "Design notes" for why this is a separate, much larger cap than the one bounding the LLM prompt.
- **No spam/cost control on `attest()`** beyond the URL-length caps - a production deployment serving untrusted callers would likely want a small fee, mirroring the fee mechanisms already used elsewhere in this account's contracts.
- **`ListingGate` doesn't auto-revoke** when AuditScope's verdict later changes to `MISMATCH` - `revoke_listing` exists but has to be called explicitly; a v2 would want this triggered automatically whenever AuditScope records a new attestation for a listed target.
