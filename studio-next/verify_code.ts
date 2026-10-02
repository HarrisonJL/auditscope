// Confirms the code deployed on Studio Next is byte-identical to this repo's
// source (same SHA-256), fetched straight from the chain.
//
//   npx tsx verify_code.ts                      # AuditScope at the reviewed address
//   npx tsx verify_code.ts <address> <file>     # any other deployment / source file
import { createClient, chains } from "genlayer-js";
import * as crypto from "crypto";
import * as fs from "fs";

const REVIEWED = "0x3B3c8317f24e394A24520D5f382E95bdb6f2be40";

async function main() {
  const address = process.argv[2] ?? REVIEWED;
  const file = process.argv[3] ?? "../contracts/auditscope_studio_next.py";
  const client: any = createClient({ chain: (chains as any).studioDevnet });
  let onchain: any = await client.getContractCode(address);
  if (typeof onchain !== "string") onchain = Buffer.from(onchain).toString("utf-8");
  const local = fs.readFileSync(file, "utf-8");
  const sha = (s: string) => crypto.createHash("sha256").update(s).digest("hex");
  console.log(`${address}`);
  console.log(`  on-chain  sha256 ${sha(onchain)} (${onchain.length} chars)`);
  console.log(`  ${file} sha256 ${sha(local)} (${local.length} chars)`);
  console.log(`  fail-closed reference check present on-chain: ${onchain.includes("_reference_verified")}`);
  console.log(onchain === local ? "IDENTICAL" : "DIFFERENT");
  process.exit(onchain === local ? 0 : 1);
}

main().catch((e) => {
  console.error(e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
