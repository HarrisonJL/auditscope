// Live-proves the exact steward-flagged scenario: a genuinely grounded
// audit reference (really present in the report) that does not identify
// the specific audited source being compared. audited_source_url and
// deployed_source_url are the SAME page (so the hash comparison alone
// would say MATCH), but the report is genuinely about a different
// contract entirely - reference_verified must be false and the verdict
// must be UNVERIFIED, never MATCH.
//
// Usage: npx tsx register_unverified_demo.ts <auditscope_address>
import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";

const RAW_BASE = "https://raw.githubusercontent.com/HarrisonJL/auditscope/main/demo";

function safeJson(value: unknown): string {
  return JSON.stringify(value, (_key, v) => (typeof v === "bigint" ? v.toString() : v));
}

async function writeAndWait(client: any, address: string, functionName: string, args: unknown[]) {
  const fees = await client.estimateTransactionFees({});
  const txHash = await client.writeContract({
    address, functionName, args,
    fees: { distribution: fees.distribution, feeValue: fees.feeValue },
  });
  console.log(`${functionName}(${JSON.stringify(args[0] ?? "")}) submitted ${txHash} - waiting...`);
  const receipt: any = await client.waitForTransactionReceipt({ hash: txHash, waitUntil: "finalized", interval: 5000, retries: 60 });
  console.log(`  -> ${receipt.txExecutionResultName}`);
}

async function main() {
  const asAddress = process.argv[2];
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: (chains as any).studioDevnet, account });
  console.log(`Acting as ${account.address}, AuditScope at ${asAddress}`);

  await writeAndWait(client, asAddress, "register_target", [
    "UNVERIFIED1", "ExampleVault (audit report is for a different contract)",
    `${RAW_BASE}/unrelated_audit_report.md`, `${RAW_BASE}/vault_source_v1.md`, `${RAW_BASE}/vault_source_v1.md`,
  ]);
  await writeAndWait(client, asAddress, "attest", ["UNVERIFIED1"]);

  const a: any = await client.readContract({ address: asAddress, functionName: "get_attestation", args: [2] });
  console.log("get_attestation(UNVERIFIED1):", safeJson(a));
  const covered: any = await client.readContract({ address: asAddress, functionName: "is_covered", args: ["UNVERIFIED1"] });
  console.log("is_covered(UNVERIFIED1):", covered);
}
main().catch((err) => {
  console.error(err);
  process.exit(1);
});
