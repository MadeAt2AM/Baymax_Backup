/**
 * Single-operator auth wrapper for the dashboard.
 *
 * The dashboard itself uses a session cookie. The login is a single
 * username/password exchange that returns a Set-Cookie. From that point
 * on, all requests carry the credential via `credentials: "same-origin"`.
 */

export class AuthError extends Error {
  constructor(public readonly statusCode: number, message: string) {
    super(message);
    this.name = "AuthError";
  }
}

export interface DashboardUser {
  username: string;
}

export async function login(
  username: string,
  password: string,
): Promise<DashboardUser> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // ignore
    }
    throw new AuthError(response.status, detail);
  }
  return (await response.json()) as DashboardUser;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "same-origin",
  });
}

export async function me(): Promise<DashboardUser | null> {
  const response = await fetch("/api/auth/me", {
    method: "GET",
    credentials: "same-origin",
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new AuthError(response.status, `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as DashboardUser;
}
