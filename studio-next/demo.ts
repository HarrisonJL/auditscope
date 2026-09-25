// Registers a MATCH target (deployed source unchanged since audit) and a
// MISMATCH target (owner check quietly removed post-audit), attests both,
// then deploys ListingGate and exercises it against the real MATCH result.
//
// Usage: npx tsx demo.ts <auditscope_address>
import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";
import * as fs from "fs";

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
  console.log(`  -> ${receipt.txExecutionResultName} status_name=${receipt.status_name} result_name=${receipt.result_name}`);
  return receipt;
}

async function deployContract(client: any, fileName: string, args: unknown[]) {
  const code = fs.readFileSync(`../contracts/${fileName}`, "utf-8");
  const fees = await client.estimateTransactionFees({});
  const txHash = await client.deployContract({ code, args, fees: { distribution: fees.distribution, feeValue: fees.feeValue } });
  console.log(`Deploying ${fileName} - tx ${txHash} - waiting...`);
  const receipt: any = await client.waitForTransactionReceipt({ hash: txHash, waitUntil: "finalized", interval: 5000, retries: 60 });
  const address = receipt.to_address ?? receipt.recipient;
  console.log(`  -> deployed at ${address} (${receipt.txExecutionResultName})`);
  return address;
}

async function main() {
  const asAddress = process.argv[2];
  if (!asAddress) throw new Error("Usage: tsx demo.ts <auditscope_address>");

  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: (chains as any).studioDevnet, account });
  console.log(`Acting as ${account.address}, AuditScope at ${asAddress}`);

  await writeAndWait(client, asAddress, "register_target", [
    "MATCH1", "ExampleVault (unchanged since audit)",
    `${RAW_BASE}/audit_report_match.md`, `${RAW_BASE}/vault_source_v1.md`, `${RAW_BASE}/vault_source_v1.md`,
  ]);
  await writeAndWait(client, asAddress, "register_target", [
    "MISMATCH1", "ExampleVault (owner check removed post-audit)",
    `${RAW_BASE}/audit_report_match.md`, `${RAW_BASE}/vault_source_v1.md`, `${RAW_BASE}/vault_source_v2_modified.md`,
  ]);

  await writeAndWait(client, asAddress, "attest", ["MATCH1"]);
  await writeAndWait(client, asAddress, "attest", ["MISMATCH1"]);

  const state: any = await client.readContract({ address: asAddress, functionName: "get_state", args: [] });
  console.log("\nAuditScope get_state():", state);
  for (let i = 0; i < Number(state.attestation_count); i++) {
    const a = await client.readContract({ address: asAddress, functionName: "get_attestation", args: [i] });
    console.log(`get_attestation(${i}):`, safeJson(a));
  }

  const lgAddress = await deployContract(client, "listing_gate_studio_next.py", [asAddress]);
  await writeAndWait(client, lgAddress, "request_listing", ["MATCH1"]);
  const listing: any = await client.readContract({ address: lgAddress, functionName: "get_listing", args: ["MATCH1"] });
  console.log("\nListingGate get_listing(MATCH1):", safeJson(listing));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
