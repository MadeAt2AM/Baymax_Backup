import { useCallback, useState } from "react";

import { useAuth } from "../lib/auth-context";
import { AuthError } from "../lib/auth";

import styles from "../lib/styles.module.css";

export function LoginPage() {
  const { signIn } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setSubmitting(true);
      try {
        // signIn updates the AuthContext state to "authenticated", so
        // the App's router automatically swaps the anonymous branch
        // for the gated branch. No navigate() call needed.
        await signIn(username, password);
      } catch (err) {
        const message =
          err instanceof AuthError ? err.message : "Login failed";
        setError(message);
      } finally {
        setSubmitting(false);
      }
    },
    [username, password, signIn],
  );

  return (
    <main className={styles.loginPage}>
      <div className={styles.loginCard}>
        <h1>Competitors Intelligence</h1>
        <form className={styles.loginForm} onSubmit={handleSubmit}>
          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <p className={styles.error}>{error}</p>}
          <button
            type="submit"
            className={styles.submit}
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}
