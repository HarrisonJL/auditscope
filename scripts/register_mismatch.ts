import { createClient, createAccount } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import "dotenv/config";

const RAW_BASE = "https://raw.githubusercontent.com/HarrisonJL/auditscope/main/demo";

async function main() {
  const asAddress = process.argv[2];
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: testnetBradbury, account });
  console.log(`Acting as ${account.address}, AuditScope at ${asAddress}`);

  const txHash = await client.writeContract({
    address: asAddress, functionName: "register_target",
    args: [
      "MISMATCH1", "ExampleVault (owner check removed post-audit)",
      `${RAW_BASE}/audit_report_match.md`, `${RAW_BASE}/vault_source_v1.md`, `${RAW_BASE}/vault_source_v2_modified.md`,
    ],
    value: 0n,
  });
  console.log(`register_target(MISMATCH1) submitted ${txHash} - waiting for ACCEPTED...`);
  const receipt: any = await client.waitForTransactionReceipt({
    hash: txHash as `0x${string}` & { length: 66 },
    status: "ACCEPTED" as any,
    interval: 10000,
    retries: 60,
  });
  console.log(`  -> ${receipt.txExecutionResultName} (statusName=${receipt.statusName})`);
}
main().catch((err) => {
  console.error(err);
  process.exit(1);
});
