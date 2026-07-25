/**
 * In-dashboard Instagram auth banner.
 *
 * The banner shows the current OpenCLI `whoami` state and provides the
 * paste-cookie reauthentication flow. When state is not "ok", the banner
 * shows DevTools extraction instructions for the `sessionid` and
 * `ds_user_id` cookies from a Chrome where the operator logged in to
 * Instagram directly.
 *
 * The cookies are never logged to the browser console and never
 * persisted in local storage. They are sent to the API over the same
 * session cookie the dashboard is already authenticated with.
 */

import { useCallback, useEffect, useState } from "react";

import {
  completeReauth,
  fetchStatus,
  logout,
  startReauth,
  InstagramAuthError,
  type InstagramAuthStatus,
} from "../lib/instagram-auth";

import styles from "../lib/InstagramAuthBanner.module.css";

const INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/";

interface FormState {
  reauthToken: string | null;
  sessionid: string;
  ds_user_id: string;
  error: string | null;
  submitting: boolean;
}

const INITIAL_FORM: FormState = {
  reauthToken: null,
  sessionid: "",
  ds_user_id: "",
  error: null,
  submitting: false,
};

function bannerClass(state: string | undefined): string {
  if (state === "ok") return `${styles.banner} ${styles.bannerOk}`;
  if (state === "wrong-account") return `${styles.banner} ${styles.bannerError}`;
  if (state === "browser-bridge-disconnected" || state === "no-profile") {
    return `${styles.banner} ${styles.bannerWarn}`;
  }
  return `${styles.banner} ${styles.bannerError}`;
}

function statusLabel(s: InstagramAuthStatus): string {
  switch (s.state) {
    case "ok":
      return `Authenticated as ${s.authenticated_account ?? "(unknown)"}`;
    case "wrong-account":
      return `Wrong account: ${s.authenticated_account ?? "(unknown)"}, approved is ${s.approved_account ?? "(unknown)"}`;
    case "browser-bridge-disconnected":
      return "Browser Bridge disconnected";
    case "no-profile":
      return "No OpenCLI site-session yet";
    case "no-check-yet":
      return "Not yet checked";
    case "error":
      return "Error checking authentication";
    default:
      return s.state;
  }
}

export function InstagramAuthBanner() {
  const [status, setStatus] = useState<InstagramAuthStatus | null>(null);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);

  const reload = useCallback(async () => {
    try {
      const s = await fetchStatus();
      setStatus(s);
    } catch (err) {
      if (err instanceof InstagramAuthError) {
        setStatus({
          state: "error",
          authenticated_account: null,
          approved_account: null,
          last_checked_at: new Date().toISOString(),
          message: err.message,
        });
      }
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleOpenInstagram = useCallback(() => {
    window.open(INSTAGRAM_LOGIN_URL, "_blank", "noopener,noreferrer");
  }, []);

  const handleSubmit = useCallback(async () => {
    setForm((prev) => ({ ...prev, submitting: true, error: null }));
    // Step 1: ensure we have a fresh state token. If we already have one
    // in component state, try it first; on failure, request a new one
    // because the previous token may have been consumed (the backend
    // marks tokens as single-use).
    let token = form.reauthToken;
    if (!token) {
      try {
        const handle = await startReauth();
        token = handle.token;
        setForm((prev) => ({ ...prev, reauthToken: handle.token }));
      } catch (err) {
        const message =
          err instanceof InstagramAuthError
            ? err.message
            : "Failed to start reauthentication";
        setForm((prev) => ({ ...prev, submitting: false, error: message }));
        return;
      }
    }
    // Step 2: complete the reauth.
    try {
      await completeReauth(token, form.sessionid, form.ds_user_id);
      setForm(INITIAL_FORM);
      await reload();
    } catch (err) {
      // The most common failure is "state token invalid or already
      // consumed" because the user clicked twice or refreshed. Clear
      // the cached token so the next click fetches a fresh one and
      // give a clearer error message.
      const rawMessage =
        err instanceof InstagramAuthError
          ? err.message
          : "Failed to complete reauthentication";
      const isConsumed =
        err instanceof InstagramAuthError &&
        /invalid|consumed|expired/i.test(err.message);
      const message = isConsumed
        ? "Your reauth session expired. Click Authenticate again to retry."
        : rawMessage;
      setForm((prev) => ({
        ...prev,
        submitting: false,
        reauthToken: isConsumed ? null : prev.reauthToken,
        error: message,
      }));
      if (isConsumed) {
        // Refresh the banner status so the user sees the current state.
        void reload();
      }
    }
  }, [form, reload]);

  const handleLogout = useCallback(async () => {
    try {
      await logout();
      await reload();
    } catch (err) {
      const message = err instanceof InstagramAuthError ? err.message : "Failed to log out";
      setForm((prev) => ({ ...prev, error: message }));
    }
  }, [reload]);

  return (
    <section
      data-testid="instagram-auth-banner"
      className={bannerClass(status?.state)}
      role="status"
      aria-live="polite"
    >
      <h2 className={styles.bannerTitle}>Instagram authentication</h2>
      <p className={styles.bannerMessage}>
        {status ? statusLabel(status) : "Loading..."}
      </p>
      {status?.message && status.state !== "ok" && (
        <p className={styles.bannerMessage}>{status.message}</p>
      )}

      <div className={styles.warning} data-testid="auth-warning">
        <span className={styles.warningLabel}>Warning:</span><span className="sr-only"> account-ban risk</span>
        Pasting Instagram cookies into any web form carries a moderate
        account-ban risk under Instagram's anti-scraping policy. Use only
        on the dev VPS and only for the approved secondary account.
      </div>

      {status?.state !== "ok" && (
        <>
          <div className={styles.devtools} data-testid="devtools-instructions">
            <strong>How to extract the cookies from Chrome DevTools:</strong>
            <ol>
              <li>
                Open <code>https://www.instagram.com</code> in a Chrome where
                you are logged in as the approved account.
              </li>
              <li>
                Open DevTools (F12) and go to <code>Application</code> →
                <code> Cookies</code> → <code>https://www.instagram.com</code>.
              </li>
              <li>
                Find the <code>sessionid</code> cookie and copy its value
                (32-512 chars, base64-ish).
              </li>
              <li>
                Find the <code>ds_user_id</code> cookie and copy its value
                (digits only).
              </li>
              <li>
                Paste both values below and click <strong>Authenticate</strong>.
              </li>
            </ol>
          </div>

          <div className={styles.form}>
            <div className={styles.formRow}>
              <label className={styles.formLabel} htmlFor="sessionid-input">
                sessionid
              </label>
              <input
                id="sessionid-input"
                className={styles.formInput}
                value={form.sessionid}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, sessionid: e.target.value }))
                }
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            <div className={styles.formRow}>
              <label className={styles.formLabel} htmlFor="ds-user-id-input">
                ds_user_id
              </label>
              <input
                id="ds-user-id-input"
                className={styles.formInput}
                value={form.ds_user_id}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, ds_user_id: e.target.value }))
                }
                autoComplete="off"
                spellCheck={false}
              />
            </div>
          </div>

          {form.error && (
            <p className={styles.errorText} data-testid="form-error">
              {form.error}
            </p>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.button}
              onClick={handleOpenInstagram}
            >
              Open Instagram
            </button>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={handleSubmit}
              disabled={form.submitting}
              data-testid="authenticate-button"
            >
              {form.submitting ? "Authenticating..." : "Authenticate"}
            </button>
          </div>
        </>
      )}

      {status?.state === "ok" && (
        <div className={styles.actions}>
          <button
            type="button"
            className={`${styles.button} ${styles.buttonDanger}`}
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      )}
    </section>
  );
}
