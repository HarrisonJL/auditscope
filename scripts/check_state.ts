import { createClient, createAccount } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import "dotenv/config";

async function main() {
  const address = process.argv[2];
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: testnetBradbury, account });
  const state = await client.readContract({ address, functionName: "get_state", args: [] });
  console.log("get_state():", state);
  const targets = await client.readContract({ address, functionName: "list_targets", args: [] });
  console.log("list_targets():", targets);
}
main().catch((e) => { console.error(e); process.exit(1); });
