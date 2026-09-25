import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";
import * as fs from "fs";

async function main() {
  const fileName = process.argv[2] ?? "auditscope_studio_next.py";
  const args = process.argv.slice(3);
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: (chains as any).studioDevnet, account });
  console.log(`Acting as ${account.address}`);

  const code = fs.readFileSync(`../contracts/${fileName}`, "utf-8");
  const fees = await client.estimateTransactionFees({});
  const txHash = await client.deployContract({
    code, args,
    fees: { distribution: fees.distribution, feeValue: fees.feeValue },
  });
  console.log(`Deploy tx: ${txHash}`);

  const receipt: any = await client.waitForTransactionReceipt({
    hash: txHash, waitUntil: "finalized", interval: 5000, retries: 60,
  });
  console.log("txExecutionResultName:", receipt.txExecutionResultName);
  const address = receipt.to_address ?? receipt.recipient;
  console.log("Contract address:", address);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
