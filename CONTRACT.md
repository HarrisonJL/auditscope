# Deployment

- **Address:** [`0x102fb8495D68c68317422A62519365b1687A15dc`](https://explorer-studio-dev.genlayer.com/address/0x102fb8495D68c68317422A62519365b1687A15dc)
- **Network:** GenLayer Studio Next (chain id `61997`)
- **Deploy tx:** `0x40a0d45dbe9bfa132f42ba48781735f0800b2aed9be0582624ac6b0be5b0b181`
- **Deployer:** `0x5cdb5699bc1038e115A973bb91A646f7E98C075b`
- **Contract source:** [`contracts/auditscope_studio_next.py`](contracts/auditscope_studio_next.py) - functionally identical to [`contracts/auditscope.py`](contracts/auditscope.py); only GenVM import/decorator conventions differ. Ported using the mechanical process already proven on SolvencyOracle and QuoteKeeper - both contracts (this one and `listing_gate.py`) passed their live schema check on the first try, including the `gl.get_contract_at` -> `gl.contract.get_at` fix QuoteKeeper's port already found.

## Live proof: a MATCH and a MISMATCH, both correct, both on the first try

Two demo targets registered against real, public pages, telling one coherent story: the same
audit report and the same audited source, but two different "currently deployed" states.

- `register_target("MATCH1", ...)` - tx `0xf283df2e456e80e29a663329417eec2229b33fb49b694aee9437431c4184d2d0`
- `register_target("MISMATCH1", ...)` - tx `0x361bc40584b519b0969d1652f4d4e2b1e9c16b962980f1edaa57c3e17fb955e0`

`attest("MATCH1")` - tx `0xe8df62a2bb673491657d7d30de6fd8e67fc15a6738f97e0672372c3bb2c8de95`:

```json
{
  "claimed_reference": "audited at commit `e4f1a9c`",
  "grounded": true,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "verdict": "MATCH"
}
```

The LLM correctly quoted a verbatim phrase from the report ("audited at commit `e4f1a9c`" - a substring of the report's actual sentence), the validator confirmed it was genuinely grounded, and both parties independently computed the identical hash for the audited and deployed source (both pointed at the same page for this target) - **MATCH**, correctly.

`attest("MISMATCH1")` - tx `0x505f19fc1f2e13cbf970b75844a347ae27222569d92b5e61cd2eede33bfa16c7`:

```json
{
  "claimed_reference": "audited at commit `e4f1a9c`",
  "grounded": true,
  "audited_hash": "70813bcac8f222cf0149dc19217a839cf5078cf6bea921aa91364f8be43cb910",
  "deployed_hash": "2cebdd14c4446b7666e9f11005b55695055214ca9e1b17627aea9aad4c7da5b9",
  "verdict": "MISMATCH"
}
```

Same audit, same audited source - but this target's `deployed_source_url` points at [a version with the owner check quietly removed](demo/vault_source_v2_modified.md), and the deployed hash correctly differs from the audited hash - **MISMATCH**, correctly, and a genuinely different verdict from MATCH1's, proving the oracle isn't rubber-stamping every target as covered.

## Live proof: composability, including a real negative case

[`contracts/listing_gate_studio_next.py`](contracts/listing_gate_studio_next.py) demonstrates a downstream contract gating on `is_covered()` via a real cross-contract call.

- Deploy - tx `0x1623cab9904b4e4c0c1729c4a5e9539cb6198b48e559424fe737ba29bf0f7bf4` (address `0x3d67bA0A35a0719A37A286319095cD2291764CcA`)
- `request_listing("MATCH1")` - tx `0xf4e5c8dbe1a95620b42af67eeee5579618df5cedbcc6378428cd40001b9d23c7`: succeeded. `is_listed("MATCH1")` reads `true`.
- `request_listing("MISMATCH1")` - tx `0xf9f4eb6fbaafb75063fb9e144fe023c29e2afc0dd996917ab6e94a2d040af6e7`: **correctly rejected** - `FINISHED_WITH_ERROR`, the contract's own `assert covered` firing because AuditScope's real, consensus-derived `is_covered("MISMATCH1")` is `false`. `is_listed("MISMATCH1")` reads `false`. Kept in this record rather than only showing the success case, since a gate that only demonstrates the positive path hasn't actually proven it gates anything.

## Historical: Bradbury deployment (partial - see below)

- **Address:** [`0xF612bf82192762adc4631c888F7639d9e728079E`](https://explorer-bradbury.genlayer.com/address/0xF612bf82192762adc4631c888F7639d9e728079E)
- **Deploy tx:** `0xe27d3120b366b756c70077866efdb9143c4dfd257a3555600648adc523ea6d86`

Both demo targets registered successfully and confirmed live:

- `register_target("MATCH1")` - tx `0xf207b60e3c00afd0884d4eb718267c9fac4bdef2aae8c9fffe7646da0460b5ad`: reached `ACCEPTED` cleanly (`resultName: AGREE`, `FINISHED_WITH_RETURN`) - confirmed directly via `getTransaction()`, not assumed from a client-side timeout.
- `register_target("MISMATCH1")` - tx `0x47909325fc06123f7af880b403563c74898f28a519a7c316845f12d93a54a456`: succeeded on the third attempt, after one RPC gas-rate-limit (`node is at capacity`) and one raw EVM/consensus-contract revert on the fresh deployment - both transient infra conditions already documented elsewhere in this account's work, not code issues.

`attest("MATCH1")` (tx `0xb15d6ff72bf6051691de19734ebf6313781715d57ec158bea4bf2673f6a533f8`) was submitted and, at time of writing, was confirmed via direct `getTransaction()` inspection to still be genuinely mid-consensus (`status: COMMITTING`, `txExecutionResultName: NOT_VOTED`) after an extended wait - not stuck or failed, just slow, on a night Bradbury's RPC was independently observed rate-limiting and reverting fresh deployments. Given the complete attestation flow (registration through the composability example) is already proven live and correct on Studio Next above, this was not pursued further to finality - Bradbury's role in this account's pattern is a secondary "works on more than one network" data point, not the primary deployment, and chasing a slow network on a bad night past the point of diminishing evidence wasn't worth it. The transaction may well finalize on its own; this record reflects its state honestly rather than waiting indefinitely to report a result.
