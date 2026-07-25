/**
 * Auth context for the dashboard.
 *
 * The dashboard uses a single session cookie that the API sets on
 * `/api/auth/login`. The App component needs to know whether the
 * current browser is authenticated so it can decide which routes to
 * render (login page vs. gated pages).
 *
 * This context wraps the App and exposes:
 *   - `auth`: "loading" | "anonymous" | "authenticated"
 *   - `username`: the operator name when authenticated
 *   - `refresh()`: re-run the `/api/auth/me` check
 *   - `signIn(username, password)`: log in, set auth state
 *   - `signOut()`: log out, set auth state to anonymous
 *
 * The login and logout flows are here (not just in the page components)
 * so the App can re-render with the new auth state without a full
 * page reload.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { AuthError, me } from "./auth";

type AuthState = "loading" | "anonymous" | "authenticated";

interface AuthContextValue {
  auth: AuthState;
  username: string | null;
  /** Force a re-check of the session cookie. */
  refresh: () => Promise<void>;
  /**
   * Log in. On success, the auth state flips to "authenticated" and
   * the username is set. The caller does not need to navigate — the
   * App's render is driven by `auth`.
   */
  signIn: (username: string, password: string) => Promise<void>;
  /**
   * Log out. On success, the auth state flips to "anonymous". The
   * caller does not need to navigate.
   */
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [auth, setAuth] = useState<AuthState>("loading");
  const [username, setUsername] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const user = await me();
      if (user) {
        setAuth("authenticated");
        setUsername(user.username);
      } else {
        setAuth("anonymous");
        setUsername(null);
      }
    } catch (err) {
      // Treat any unexpected error as anonymous — the user can re-login.
      if (err instanceof AuthError) {
        setAuth("anonymous");
        setUsername(null);
      } else {
        setAuth("anonymous");
        setUsername(null);
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(
    async (u: string, password: string) => {
      // We import lazily to avoid a circular dep at module load.
      const { login } = await import("./auth");
      const user = await login(u, password);
      setUsername(user.username);
      setAuth("authenticated");
    },
    [],
  );

  const signOut = useCallback(async () => {
    const { logout } = await import("./auth");
    await logout();
    setAuth("anonymous");
    setUsername(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ auth, username, refresh, signIn, signOut }),
    [auth, username, refresh, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
