import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";

function safeJson(value: unknown): string {
  return JSON.stringify(value, (_key, v) => (typeof v === "bigint" ? v.toString() : v));
}

async function main() {
  const asAddress = process.argv[2];
  const targetId = process.argv[3];
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: (chains as any).studioDevnet, account });

  const fees = await client.estimateTransactionFees({});
  const txHash = await client.writeContract({
    address: asAddress, functionName: "attest", args: [targetId],
    fees: { distribution: fees.distribution, feeValue: fees.feeValue },
  });
  console.log(`attest(${targetId}) submitted ${txHash} - waiting...`);
  const receipt: any = await client.waitForTransactionReceipt({ hash: txHash, waitUntil: "finalized", interval: 5000, retries: 60 });
  console.log(`  -> ${receipt.txExecutionResultName} status_name=${receipt.status_name} result_name=${receipt.result_name}`);

  const state: any = await client.readContract({ address: asAddress, functionName: "get_state", args: [] });
  console.log("get_state():", state);
  if (Number(state.attestation_count) > 0) {
    const a = await client.readContract({ address: asAddress, functionName: "get_attestation", args: [Number(state.attestation_count) - 1] });
    console.log("latest attestation:", safeJson(a));
  }
}
main().catch((err) => {
  console.error(err);
  process.exit(1);
});
