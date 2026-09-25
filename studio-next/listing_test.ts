import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";

function safeJson(value: unknown): string {
  return JSON.stringify(value, (_key, v) => (typeof v === "bigint" ? v.toString() : v));
}

async function main() {
  const lgAddress = process.argv[2];
  const targetId = process.argv[3];
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: (chains as any).studioDevnet, account });

  const fees = await client.estimateTransactionFees({});
  const txHash = await client.writeContract({
    address: lgAddress, functionName: "request_listing", args: [targetId],
    fees: { distribution: fees.distribution, feeValue: fees.feeValue },
  });
  console.log(`request_listing(${targetId}) submitted ${txHash} - waiting...`);
  const receipt: any = await client.waitForTransactionReceipt({ hash: txHash, waitUntil: "finalized", interval: 5000, retries: 60 });
  console.log(`  -> ${receipt.txExecutionResultName}`);

  const isListed = await client.readContract({ address: lgAddress, functionName: "is_listed", args: [targetId] });
  console.log(`is_listed(${targetId}):`, isListed);
  const listing: any = await client.readContract({ address: lgAddress, functionName: "get_listing", args: [targetId] });
  console.log("get_listing:", safeJson(listing));
}
main().catch((err) => {
  console.error(err);
  process.exit(1);
});
