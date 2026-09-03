#!/usr/bin/env node
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { mkdir, readdir, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve, sep } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const CODEX_EXTENSION_ID = "hehggadaopoacecdllhhajmbjkdcmajg";
export const CODEX_EXTENSION_HOST_NAME = "com.openai.codexextension";
export const CODEX_CRX_URL =
  "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0.0.0&acceptformat=crx2,crx3&x=id%3Dhehggadaopoacecdllhhajmbjkdcmajg%26installsource%3Dondemand%26uc";

export function chromeWebStoreCrxUrl(extensionId, prodVersion = "120.0.0.0") {
  return `https://clients2.google.com/service/update2/crx?response=redirect&prodversion=${encodeURIComponent(
    prodVersion,
  )}&acceptformat=crx2,crx3&x=id%3D${encodeURIComponent(extensionId)}%26installsource%3Dondemand%26uc`;
}

export function encodeVarint(value) {
  let v = BigInt(value);
  const bytes = [];
  do {
    let byte = Number(v & 0x7fn);
    v >>= 7n;
    if (v !== 0n) byte |= 0x80;
    bytes.push(byte);
  } while (v !== 0n);
  return Buffer.from(bytes);
}

export function encodeLengthDelimited(field, value) {
  const body = Buffer.from(value);
  return Buffer.concat([encodeVarint((field << 3) | 2), encodeVarint(body.length), body]);
}

function readVarint(buffer, state) {
  let result = 0n;
  let shift = 0n;
  while (state.offset < buffer.length) {
    const byte = BigInt(buffer[state.offset++]);
    result |= (byte & 0x7fn) << shift;
    if ((byte & 0x80n) === 0n) return Number(result);
    shift += 7n;
  }
  throw new Error("Unterminated protobuf varint.");
}

export function readProtobufFields(buffer) {
  const fields = [];
  const state = { offset: 0 };
  while (state.offset < buffer.length) {
    const tag = readVarint(buffer, state);
    const field = tag >> 3;
    const wire = tag & 7;
    let value;
    if (wire === 0) {
      value = readVarint(buffer, state);
    } else if (wire === 1) {
      value = buffer.subarray(state.offset, state.offset + 8);
      state.offset += 8;
    } else if (wire === 2) {
      const length = readVarint(buffer, state);
      value = buffer.subarray(state.offset, state.offset + length);
      state.offset += length;
    } else if (wire === 5) {
      value = buffer.subarray(state.offset, state.offset + 4);
      state.offset += 4;
    } else {
      throw new Error(`Unsupported protobuf wire type: ${wire}.`);
    }
    if (state.offset > buffer.length) throw new Error("Malformed protobuf field length.");
    fields.push({ field, wire, value });
  }
  return fields;
}

function idFromDigestBytes(bytes) {
  return Array.from(bytes, (byte) =>
    ((byte >> 4).toString(16) + (byte & 15).toString(16)).replace(/[0-9a-f]/g, (char) =>
      String.fromCharCode("a".charCodeAt(0) + Number.parseInt(char, 16)),
    ),
  ).join("");
}

export function extensionIdFromPublicKey(publicKey) {
  const digest = createHash("sha256").update(publicKey).digest().subarray(0, 16);
  return idFromDigestBytes(digest);
}

export function parseCrx3(crxBuffer) {
  if (crxBuffer.subarray(0, 4).toString("ascii") !== "Cr24") {
    throw new Error("File is not a Chrome CRX package.");
  }
  const version = crxBuffer.readUInt32LE(4);
  if (version !== 3) throw new Error(`Expected CRX3, got CRX${version}.`);
  const headerSize = crxBuffer.readUInt32LE(8);
  const zipOffset = 12 + headerSize;
  const header = crxBuffer.subarray(12, zipOffset);
  const payload = crxBuffer.subarray(zipOffset);
  const headerFields = readProtobufFields(header);
  const publicKeys = [];
  for (const entry of headerFields.filter((field) => field.field === 2 && field.wire === 2)) {
    const proofFields = readProtobufFields(entry.value);
    const publicKey = proofFields.find((field) => field.field === 1 && field.wire === 2)?.value;
    if (publicKey) {
      publicKeys.push({
        id: extensionIdFromPublicKey(publicKey),
        keyBase64: Buffer.from(publicKey).toString("base64"),
      });
    }
  }
  const signedHeaderData = headerFields.find((field) => field.field === 10000 && field.wire === 2)?.value;
  let signedHeaderId = null;
  if (signedHeaderData) {
    const signedFields = readProtobufFields(signedHeaderData);
    const crxId = signedFields.find((field) => field.field === 1 && field.wire === 2)?.value;
    if (crxId && crxId.length === 16) signedHeaderId = idFromDigestBytes(crxId);
  }
  return { version, headerSize, zipOffset, payload, publicKeys, signedHeaderId };
}

export function selectPublicKey(parsedCrx, wantedId = CODEX_EXTENSION_ID) {
  const selected = parsedCrx.publicKeys.find((candidate) => candidate.id === wantedId);
  if (!selected) {
    const candidates = parsedCrx.publicKeys.map((candidate) => candidate.id).join(", ") || "none";
    throw new Error(`Could not find a CRX public key for ${wantedId}. Candidates: ${candidates}.`);
  }
  return selected;
}

function ensureInside(parent, child) {
  const parentPath = resolve(parent);
  const childPath = resolve(child);
  const rel = relative(parentPath, childPath);
  if (rel === ".." || rel.startsWith(`..${sep}`) || resolve(rel) === rel) {
    throw new Error(`Refusing to operate outside ${parentPath}: ${childPath}`);
  }
}

function removeIfExists(path, parent) {
  if (!existsSync(path)) return;
  ensureInside(parent, path);
  rmSync(path, { recursive: true, force: true });
}

async function copyDirectory(source, destination) {
  await mkdir(destination, { recursive: true });
  for (const entry of await readdir(source, { withFileTypes: true })) {
    const sourcePath = join(source, entry.name);
    const destinationPath = join(destination, entry.name);
    if (entry.isDirectory()) await copyDirectory(sourcePath, destinationPath);
    else if (entry.isFile()) writeFileSync(destinationPath, readFileSync(sourcePath));
  }
}

function expandZip(zipPath, destination) {
  if (process.platform === "win32") {
    execFileSync("powershell", [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-Command",
      `Expand-Archive -LiteralPath '${zipPath.replaceAll("'", "''")}' -DestinationPath '${destination.replaceAll("'", "''")}' -Force`,
    ]);
    return;
  }
  execFileSync("unzip", ["-q", zipPath, "-d", destination]);
}

function crc32(buffer) {
  let table = crc32.table;
  if (!table) {
    table = crc32.table = Array.from({ length: 256 }, (_, index) => {
      let value = index;
      for (let bit = 0; bit < 8; bit++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
      return value >>> 0;
    });
  }
  let crc = 0xffffffff;
  for (const byte of buffer) crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function dosDateTime(date = new Date()) {
  const year = Math.max(date.getFullYear(), 1980);
  const dosTime = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const dosDate = ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { dosDate, dosTime };
}

function uint16(value) {
  const buffer = Buffer.alloc(2);
  buffer.writeUInt16LE(value);
  return buffer;
}

function uint32(value) {
  const buffer = Buffer.alloc(4);
  buffer.writeUInt32LE(value >>> 0);
  return buffer;
}

export async function listFilesRecursive(sourceDir, baseDir = sourceDir) {
  const files = [];
  for (const entry of await readdir(sourceDir, { withFileTypes: true })) {
    const entryPath = join(sourceDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFilesRecursive(entryPath, baseDir)));
    } else if (entry.isFile()) {
      files.push({
        absolutePath: entryPath,
        zipPath: relative(baseDir, entryPath).split(sep).join("/"),
      });
    }
  }
  return files.sort((a, b) => a.zipPath.localeCompare(b.zipPath));
}

export async function writeStoreZip(sourceDir, zipPath) {
  await mkdir(dirname(zipPath), { recursive: true });
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  const { dosDate, dosTime } = dosDateTime();
  for (const file of await listFilesRecursive(sourceDir)) {
    const name = Buffer.from(file.zipPath, "utf8");
    const data = readFileSync(file.absolutePath);
    const crc = crc32(data);
    const localHeader = Buffer.concat([
      uint32(0x04034b50),
      uint16(20),
      uint16(0x0800),
      uint16(0),
      uint16(dosTime),
      uint16(dosDate),
      uint32(crc),
      uint32(data.length),
      uint32(data.length),
      uint16(name.length),
      uint16(0),
      name,
    ]);
    localParts.push(localHeader, data);
    centralParts.push(
      Buffer.concat([
        uint32(0x02014b50),
        uint16(20),
        uint16(20),
        uint16(0x0800),
        uint16(0),
        uint16(dosTime),
        uint16(dosDate),
        uint32(crc),
        uint32(data.length),
        uint32(data.length),
        uint16(name.length),
        uint16(0),
        uint16(0),
        uint16(0),
        uint16(0),
        uint32(0),
        uint32(offset),
        name,
      ]),
    );
    offset += localHeader.length + data.length;
  }
  const centralDirectory = Buffer.concat(centralParts);
  const end = Buffer.concat([
    uint32(0x06054b50),
    uint16(0),
    uint16(0),
    uint16(centralParts.length),
    uint16(centralParts.length),
    uint32(centralDirectory.length),
    uint32(offset),
    uint16(0),
  ]);
  writeFileSync(zipPath, Buffer.concat([...localParts, centralDirectory, end]));
}

async function compressDirectory(sourceDir, zipPath) {
  await writeStoreZip(sourceDir, zipPath);
}

async function downloadCrx(destination, crxUrl = CODEX_CRX_URL) {
  const response = await fetch(crxUrl, { redirect: "follow" });
  if (!response.ok) throw new Error(`Failed to download CRX: HTTP ${response.status}.`);
  writeFileSync(destination, Buffer.from(await response.arrayBuffer()));
}

export async function buildStableIdExtension({
  crxPath,
  crxUrl = CODEX_CRX_URL,
  outputDir,
  wantedId = CODEX_EXTENSION_ID,
  projectName = "codex-chrome-extension",
  writeZip = true,
  keepUpdateUrl = true,
}) {
  const root = resolve(outputDir);
  await mkdir(root, { recursive: true });
  const finalDir = join(root, projectName);
  const finalZip = join(root, `${projectName}.zip`);
  const crxFile = crxPath ? resolve(crxPath) : join(root, `${projectName}.crx`);
  if (!crxPath || !existsSync(crxFile)) await downloadCrx(crxFile, crxUrl);

  removeIfExists(finalDir, root);
  if (writeZip) removeIfExists(finalZip, root);

  const crxBuffer = readFileSync(crxFile);
  const parsedCrx = parseCrx3(crxBuffer);
  const selectedKey = selectPublicKey(parsedCrx, wantedId);
  const tempDir = mkdtempSync(join(tmpdir(), "codex-chrome-extension-"));
  const payloadZip = join(tempDir, "payload.zip");
  const unpackedDir = join(tempDir, "unpacked");
  writeFileSync(payloadZip, parsedCrx.payload);
  await mkdir(unpackedDir, { recursive: true });
  expandZip(payloadZip, unpackedDir);

  const manifestPath = join(unpackedDir, "manifest.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  manifest.key = selectedKey.keyBase64;
  if (!keepUpdateUrl) delete manifest.update_url;
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

  await copyDirectory(unpackedDir, finalDir);
  if (writeZip) await compressDirectory(finalDir, finalZip);
  rmSync(tempDir, { recursive: true, force: true });

  const manifestStat = await stat(join(finalDir, "manifest.json"));
  return {
    crxPath: crxFile,
    outputDirectory: finalDir,
    outputZip: writeZip ? finalZip : null,
    extensionId: selectedKey.id,
    signedHeaderId: parsedCrx.signedHeaderId,
    version: manifest.version,
    manifestBytes: manifestStat.size,
    publicKeyCandidates: parsedCrx.publicKeys.map((candidate) => candidate.id),
  };
}

export const buildFixedIdExtension = buildStableIdExtension;

function printUsage() {
  console.log(`Usage:
  node scripts/install_chrome_extension.mjs build --output <dir> [--crx <file>] [--crx-url <url>] [--id ${CODEX_EXTENSION_ID}] [--project-name codex-chrome-extension]
  node scripts/install_chrome_extension.mjs inspect --crx <file>

Defaults target the Codex Chrome Extension. Keep --id as ${CODEX_EXTENSION_ID} for Codex native messaging compatibility; pass another --id only for non-Codex CRX3 experiments.`);
}

function readArg(args, name, fallback = null) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  if (index === args.length - 1) throw new Error(`Missing value for ${name}.`);
  return args[index + 1];
}

export async function main(argv = process.argv.slice(2)) {
  const command = argv[0];
  if (!command || argv.includes("--help")) {
    printUsage();
    return;
  }
  if (command === "inspect") {
    const crxPath = readArg(argv, "--crx");
    if (!crxPath) throw new Error("inspect requires --crx.");
    const parsedCrx = parseCrx3(readFileSync(crxPath));
    console.log(
      JSON.stringify(
        {
          version: parsedCrx.version,
          headerSize: parsedCrx.headerSize,
          zipOffset: parsedCrx.zipOffset,
          signedHeaderId: parsedCrx.signedHeaderId,
          publicKeyCandidates: parsedCrx.publicKeys.map((candidate) => candidate.id),
        },
        null,
        2,
      ),
    );
    return;
  }
  if (command === "build") {
    const outputDir = readArg(argv, "--output");
    if (!outputDir) throw new Error("build requires --output.");
    const id = readArg(argv, "--id", CODEX_EXTENSION_ID);
    const result = await buildStableIdExtension({
      crxPath: readArg(argv, "--crx"),
      crxUrl: readArg(argv, "--crx-url", chromeWebStoreCrxUrl(id)),
      outputDir,
      wantedId: id,
      projectName: readArg(argv, "--project-name", "codex-chrome-extension"),
      writeZip: !argv.includes("--no-zip"),
      keepUpdateUrl: !argv.includes("--strip-update-url"),
    });
    console.log(JSON.stringify(result, null, 2));
    return;
  }
  throw new Error(`Unknown command: ${command}.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
