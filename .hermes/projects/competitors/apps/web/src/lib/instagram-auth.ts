/**
 * Typed wrapper for the in-dashboard Instagram auth API.
 *
 * The wrapper is deliberately small: each function returns the parsed
 * response or throws a typed error. Cookies are never returned by the
 * server, and the wrapper never logs them.
 */

export type InstagramAuthState =
  | "ok"
  | "browser-bridge-disconnected"
  | "wrong-account"
  | "no-profile"
  | "no-check-yet"
  | "error";

export interface InstagramAuthStatus {
  state: InstagramAuthState;
  authenticated_account: string | null;
  approved_account: string | null;
  last_checked_at: string;
  message: string;
}

export interface InstagramAuthReauthHandle {
  token: string;
  expires_at: number;
  approved_account: string;
}

export interface InstagramAuthCompleteResult {
  state: "ok";
  authenticated_account: string | null;
  approved_account: string | null;
}

export class InstagramAuthError extends Error {
  constructor(public readonly statusCode: number, message: string) {
    super(message);
    this.name = "InstagramAuthError";
  }
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new InstagramAuthError(response.status, detail);
  }
  return (await response.json()) as T;
}

export async function fetchStatus(): Promise<InstagramAuthStatus> {
  const response = await fetch("/api/auth/instagram/status", {
    method: "GET",
    credentials: "same-origin",
  });
  return readJson<InstagramAuthStatus>(response);
}

export async function startReauth(): Promise<InstagramAuthReauthHandle> {
  const response = await fetch("/api/auth/instagram/start", {
    method: "POST",
    credentials: "same-origin",
  });
  return readJson<InstagramAuthReauthHandle>(response);
}

export async function completeReauth(
  state: string,
  sessionid: string,
  ds_user_id: string,
): Promise<InstagramAuthCompleteResult> {
  const response = await fetch("/api/auth/instagram/complete", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state, sessionid, ds_user_id }),
  });
  return readJson<InstagramAuthCompleteResult>(response);
}

export async function logout(): Promise<{ state: "ok" }> {
  const response = await fetch("/api/auth/instagram/logout", {
    method: "POST",
    credentials: "same-origin",
  });
  return readJson<{ state: "ok" }>(response);
}
