import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync } from "node:crypto";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  CODEX_CRX_URL,
  CODEX_EXTENSION_ID,
  buildFixedIdExtension,
  buildStableIdExtension,
  chromeWebStoreCrxUrl,
  encodeLengthDelimited,
  extensionIdFromPublicKey,
  parseCrx3,
  selectPublicKey,
  writeStoreZip,
} from "../scripts/install_chrome_extension.mjs";

function publicKeyDerFromSeed() {
  const { publicKey } = generateKeyPairSync("rsa", {
    modulusLength: 2048,
    publicKeyEncoding: { type: "spki", format: "der" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
  return Buffer.from(publicKey);
}

function makeCrx3({ publicKeys, signedHeaderIdBytes, zipPayload }) {
  const proofs = publicKeys.map((publicKey) => {
    const proof = Buffer.concat([
      encodeLengthDelimited(1, publicKey),
      encodeLengthDelimited(2, Buffer.from("signature-placeholder")),
    ]);
    return encodeLengthDelimited(2, proof);
  });
  const signedHeader = encodeLengthDelimited(1, signedHeaderIdBytes);
  const header = Buffer.concat([...proofs, encodeLengthDelimited(10000, signedHeader)]);
  const prefix = Buffer.alloc(12);
  prefix.write("Cr24", 0, "ascii");
  prefix.writeUInt32LE(3, 4);
  prefix.writeUInt32LE(header.length, 8);
  return Buffer.concat([prefix, header, zipPayload]);
}

async function createZipWithManifest(zipPath) {
  const dir = mkdtempSync(join(tmpdir(), "codex-extension-fixture-"));
  writeFileSync(
    join(dir, "manifest.json"),
    JSON.stringify({
      manifest_version: 3,
      name: "Codex",
      version: "1.1.5",
      update_url: "https://clients2.google.com/service/update2/crx",
      background: { service_worker: "background.js" },
    }),
  );
  writeFileSync(join(dir, "background.js"), "console.log('fixture');\n");
  await writeStoreZip(dir, zipPath);
  return dir;
}

test("extensionIdFromPublicKey uses Chrome ID alphabet", () => {
  const publicKey = publicKeyDerFromSeed();
  const id = extensionIdFromPublicKey(publicKey);
  assert.match(id, /^[a-p]{32}$/);
});

test("parseCrx3 lists all RSA proof key candidates and signed header ID", () => {
  const firstKey = publicKeyDerFromSeed();
  const secondKey = publicKeyDerFromSeed();
  const signedHeaderBytes = Buffer.from("74766030efe02423bb7709c19a32c096", "hex");
  const crx = makeCrx3({
    publicKeys: [firstKey, secondKey],
    signedHeaderIdBytes: signedHeaderBytes,
    zipPayload: Buffer.from("PK fixture"),
  });
  const parsed = parseCrx3(crx);
  assert.equal(parsed.version, 3);
  assert.equal(parsed.signedHeaderId, CODEX_EXTENSION_ID);
  assert.deepEqual(parsed.publicKeys.map((candidate) => candidate.id), [
    extensionIdFromPublicKey(firstKey),
    extensionIdFromPublicKey(secondKey),
  ]);
});

test("selectPublicKey chooses the requested ID rather than the first candidate", () => {
  const firstKey = publicKeyDerFromSeed();
  const secondKey = publicKeyDerFromSeed();
  const secondId = extensionIdFromPublicKey(secondKey);
  const crx = makeCrx3({
    publicKeys: [firstKey, secondKey],
    signedHeaderIdBytes: Buffer.alloc(16),
    zipPayload: Buffer.from("PK fixture"),
  });
  const parsed = parseCrx3(crx);
  assert.equal(selectPublicKey(parsed, secondId).id, secondId);
  assert.notEqual(parsed.publicKeys[0].id, secondId);
});

test("buildFixedIdExtension writes manifest.key and named output project", async () => {
  const temp = mkdtempSync(join(tmpdir(), "codex-chrome-extension-test-"));
  try {
    const zipPath = join(temp, "payload.zip");
    const fixtureDir = await createZipWithManifest(zipPath);
    await rm(fixtureDir, { recursive: true, force: true });
    const publicKey = publicKeyDerFromSeed();
    const wantedId = extensionIdFromPublicKey(publicKey);
    const crx = makeCrx3({
      publicKeys: [publicKey],
      signedHeaderIdBytes: Buffer.alloc(16),
      zipPayload: readFileSync(zipPath),
    });
    const crxPath = join(temp, "fixture.crx");
    writeFileSync(crxPath, crx);
    const result = await buildFixedIdExtension({
      crxPath,
      outputDir: temp,
      wantedId,
      projectName: "codex-chrome-extension",
      writeZip: false,
    });
    assert.equal(result.extensionId, wantedId);
    assert.equal(result.outputDirectory, join(temp, "codex-chrome-extension"));
    const manifest = JSON.parse(readFileSync(join(result.outputDirectory, "manifest.json"), "utf8"));
    assert.equal(extensionIdFromPublicKey(Buffer.from(manifest.key, "base64")), wantedId);
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});

test("chromeWebStoreCrxUrl builds a CRX update URL for any extension ID", () => {
  const url = chromeWebStoreCrxUrl("abcdefghijklmnopabcdefghijklmnop", "123.0.0.0");
  assert.match(url, /^https:\/\/clients2\.google\.com\/service\/update2\/crx\?/);
  assert.match(url, /prodversion=123\.0\.0\.0/);
  assert.match(url, /id%3Dabcdefghijklmnopabcdefghijklmnop/);
});

test("Codex defaults keep the native-host-compatible extension ID fixed", () => {
  assert.equal(CODEX_EXTENSION_ID, "hehggadaopoacecdllhhajmbjkdcmajg");
  assert.match(CODEX_CRX_URL, /id%3Dhehggadaopoacecdllhhajmbjkdcmajg/);
});

test("buildStableIdExtension can strip update_url for generic unpacked builds", async () => {
  const temp = mkdtempSync(join(tmpdir(), "install-chrome-extension-test-"));
  try {
    const zipPath = join(temp, "payload.zip");
    const fixtureDir = await createZipWithManifest(zipPath);
    await rm(fixtureDir, { recursive: true, force: true });
    const publicKey = publicKeyDerFromSeed();
    const wantedId = extensionIdFromPublicKey(publicKey);
    const crx = makeCrx3({
      publicKeys: [publicKey],
      signedHeaderIdBytes: Buffer.alloc(16),
      zipPayload: readFileSync(zipPath),
    });
    const crxPath = join(temp, "fixture.crx");
    writeFileSync(crxPath, crx);
    const result = await buildStableIdExtension({
      crxPath,
      outputDir: temp,
      wantedId,
      projectName: "generic-extension",
      keepUpdateUrl: false,
      writeZip: false,
    });
    const manifest = JSON.parse(readFileSync(join(result.outputDirectory, "manifest.json"), "utf8"));
    assert.equal(manifest.update_url, undefined);
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});
