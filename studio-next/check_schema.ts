// Read-only: validates a Studio Next contract variant against the live
// runner/import conventions before spending a real deploy on it.
import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";
import * as fs from "fs";

async function main() {
  const fileName = process.argv[2] ?? "auditscope_studio_next.py";
  const rawKey = process.env.DEPLOYER_PRIVATE_KEY!;
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  const client: any = createClient({ chain: (chains as any).studioDevnet, account });
  console.log("Account:", account.address);

  const code = fs.readFileSync(`../contracts/${fileName}`, "utf-8");
  try {
    const schema = await client.getContractSchemaForCode(code);
    console.log("Schema check PASSED:", JSON.stringify(schema).slice(0, 500));
  } catch (err: any) {
    console.log("Schema check FAILED:", err?.shortMessage || err?.message || String(err));
  }
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
