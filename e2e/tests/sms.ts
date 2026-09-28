import { createClient } from "redis";

/**
 * Reads the latest SMS body for a phone from the dev/test console provider's Redis outbox
 * (`dev-sms:<E.164>`). That provider is rejected by config outside development/test.
 */
export async function latestCode(e164: string, { after = 0 } = {}): Promise<string> {
  const client = createClient({ url: process.env.REDIS_URL ?? "redis://localhost:6379/0" });
  await client.connect();
  try {
    for (let i = 0; i < 40; i++) {
      const messages = await client.lRange(`dev-sms:${e164}`, 0, -1);
      if (messages.length > after) {
        const code = /\b(\d{6})\b/.exec(messages[0] ?? "")?.[1];
        if (code) return code;
      }
      await new Promise((r) => setTimeout(r, 250));
    }
    throw new Error(`No SMS received for ${e164}`);
  } finally {
    await client.disconnect(); // QUIT is deprecated since Redis 7.2
  }
}

export async function smsCount(e164: string): Promise<number> {
  const client = createClient({ url: process.env.REDIS_URL ?? "redis://localhost:6379/0" });
  await client.connect();
  try {
    return await client.lLen(`dev-sms:${e164}`);
  } finally {
    await client.disconnect(); // QUIT is deprecated since Redis 7.2
  }
}

/** A fresh patient number per run avoids OTP rate limits between runs. */
export function randomPatientPhone(): { local: string; e164: string } {
  const digits = String(Math.floor(Math.random() * 1e8)).padStart(8, "0");
  return { local: `016${digits}`, e164: `+88016${digits}` };
}
