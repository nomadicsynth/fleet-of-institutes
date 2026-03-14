import nacl from "tweetnacl";
import { decodeBase64, encodeBase64 } from "tweetnacl-util";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

export interface Identity {
  publicKey: string; // base64
  secretKey: string; // base64
  instituteId?: string;
}

const CONFIG_DIR = join(homedir(), ".fleet-of-institutes");
const IDENTITY_PATH = join(CONFIG_DIR, "identity.json");

export function loadIdentity(): Identity | null {
  if (!existsSync(IDENTITY_PATH)) return null;
  const raw = readFileSync(IDENTITY_PATH, "utf-8");
  return JSON.parse(raw) as Identity;
}

export function saveIdentity(identity: Identity): void {
  mkdirSync(CONFIG_DIR, { recursive: true });
  writeFileSync(IDENTITY_PATH, JSON.stringify(identity, null, 2), "utf-8");
}

export function generateKeypair(): Identity {
  const pair = nacl.sign.keyPair();
  return {
    publicKey: encodeBase64(pair.publicKey),
    secretKey: encodeBase64(pair.secretKey),
  };
}

export function signBody(body: string, secretKeyB64: string): string {
  const secretKey = decodeBase64(secretKeyB64);
  const messageBytes = new TextEncoder().encode(body);
  const signed = nacl.sign.detached(messageBytes, secretKey);
  return encodeBase64(signed);
}

export function ensureIdentity(): Identity {
  let id = loadIdentity();
  if (!id) {
    id = generateKeypair();
    saveIdentity(id);
  }
  return id;
}
