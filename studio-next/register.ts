import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";

const RAW_BASE = "https://raw.githubusercontent.com/HarrisonJL/auditscope/main/demo";

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
    "MATCH1", "ExampleVault (unchanged since audit)",
    `${RAW_BASE}/audit_report_match.md`, `${RAW_BASE}/vault_source_v1.md`, `${RAW_BASE}/vault_source_v1.md`,
  ]);
  await writeAndWait(client, asAddress, "register_target", [
    "MISMATCH1", "ExampleVault (owner check removed post-audit)",
    `${RAW_BASE}/audit_report_match.md`, `${RAW_BASE}/vault_source_v1.md`, `${RAW_BASE}/vault_source_v2_modified.md`,
  ]);

  const state: any = await client.readContract({ address: asAddress, functionName: "get_state", args: [] });
  console.log("get_state():", state);
}
main().catch((err) => {
  console.error(err);
  process.exit(1);
});
