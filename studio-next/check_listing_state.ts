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

  const isListed = await client.readContract({ address: lgAddress, functionName: "is_listed", args: [targetId] });
  console.log(`is_listed(${targetId}):`, isListed);
  try {
    const listing: any = await client.readContract({ address: lgAddress, functionName: "get_listing", args: [targetId] });
    console.log("get_listing:", safeJson(listing));
  } catch (e: any) {
    console.log("get_listing threw (expected if never successfully listed):", e.shortMessage || e.message);
  }
}
main().catch((err) => {
  console.error(err);
  process.exit(1);
});
