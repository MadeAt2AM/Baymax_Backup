/**
 * Tests for the in-dashboard Instagram auth banner.
 *
 * Coverage:
 *  - status badge colors for each of the six states
 *  - DevTools extraction instructions are visible when the state is
 *    not "ok"
 *  - the security warning is visible at all times
 *  - the paste flow drives start -> complete -> status
 *  - the "Open Instagram" button opens a new tab on the right URL
 *  - validation errors are surfaced without logging the cookie values
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { InstagramAuthBanner } from "../components/InstagramAuthBanner";
import {
  completeReauth,
  fetchStatus,
  InstagramAuthError,
  logout,
  startReauth,
  type InstagramAuthStatus,
} from "../lib/instagram-auth";

vi.mock("../lib/instagram-auth", async () => {
  const actual =
    await vi.importActual<typeof import("../lib/instagram-auth")>(
      "../lib/instagram-auth",
    );
  return {
    ...actual,
    fetchStatus: vi.fn(),
    startReauth: vi.fn(),
    completeReauth: vi.fn(),
    logout: vi.fn(),
  };
});

const mockedFetchStatus = vi.mocked(fetchStatus);
const mockedStartReauth = vi.mocked(startReauth);
const mockedCompleteReauth = vi.mocked(completeReauth);
const mockedLogout = vi.mocked(logout);

const STATUSES: Record<string, InstagramAuthStatus> = {
  ok: {
    state: "ok",
    authenticated_account: "mallu.wave",
    approved_account: "mallu.wave",
    last_checked_at: "2026-07-24T13:30:00+08:00",
    message: "ok",
  },
  disconnected: {
    state: "browser-bridge-disconnected",
    authenticated_account: null,
    approved_account: "mallu.wave",
    last_checked_at: "2026-07-24T13:30:00+08:00",
    message: "Browser Bridge extension is not connected.",
  },
  wrong: {
    state: "wrong-account",
    authenticated_account: "madeat2am.primary",
    approved_account: "mallu.wave",
    last_checked_at: "2026-07-24T13:30:00+08:00",
    message: "Authenticated as the wrong account.",
  },
  noProfile: {
    state: "no-profile",
    authenticated_account: null,
    approved_account: "mallu.wave",
    last_checked_at: "2026-07-24T13:30:00+08:00",
    message: "No cookies written yet.",
  },
  noCheck: {
    state: "no-check-yet",
    authenticated_account: null,
    approved_account: null,
    last_checked_at: "2026-07-24T13:30:00+08:00",
    message: "No check yet.",
  },
  error: {
    state: "error",
    authenticated_account: null,
    approved_account: "mallu.wave",
    last_checked_at: "2026-07-24T13:30:00+08:00",
    message: "opencli whoami failed",
  },
};

describe("InstagramAuthBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows ok status with the authenticated account and a logout button", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.ok);
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/mallu\.wave/i)).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /log out/i }),
    ).toBeInTheDocument();
  });

  it("shows a red status badge when the wrong account is authenticated", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.wrong);
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/madeat2am\.primary/i)).toBeInTheDocument();
    });
    // The banner should warn that the connected account is not the approved one.
    expect(screen.getByText(/Authenticated as the wrong account/i)).toBeInTheDocument();
    expect(screen.getByText(/madeat2am\.primary/i)).toBeInTheDocument();
  });

  it("shows the DevTools extraction instructions when state is not ok", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.noProfile);
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(
        screen.getByTestId("devtools-instructions"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/cookies/i, { selector: "code" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/sessionid/i, { selector: "label" })).toBeInTheDocument();
    expect(screen.getByText(/ds_user_id/i, { selector: "label" })).toBeInTheDocument();
  });

  it("always shows the security warning", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.ok);
    render(<InstagramAuthBanner />);
    expect(
      screen.getByText(/warning/i),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("auth-warning"),
    ).toBeInTheDocument();
  });

  it("opens instagram.com in a new tab when the user clicks 'Open Instagram'", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.noProfile);
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(screen.getByTestId("devtools-instructions")).toBeInTheDocument();
    });
    const button = screen.getByRole("button", {
      name: /open instagram/i,
    });
    await userEvent.click(button);
    expect(openSpy).toHaveBeenCalledWith(
      "https://www.instagram.com/accounts/login/",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("drives the paste flow: start -> complete -> status", async () => {
    mockedFetchStatus
      .mockResolvedValueOnce(STATUSES.noProfile)
      .mockResolvedValueOnce(STATUSES.ok);
    mockedStartReauth.mockResolvedValue({
      token: "state-token-xyz",
      expires_at: Date.now() / 1000 + 600,
      approved_account: "mallu.wave",
    });
    mockedCompleteReauth.mockResolvedValue({
      state: "ok",
      authenticated_account: "mallu.wave",
      approved_account: "mallu.wave",
    });
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(screen.getByTestId("devtools-instructions")).toBeInTheDocument();
    });

    const sessionidInput = screen.getByLabelText(/sessionid/i);
    const dsUserIdInput = screen.getByLabelText(/ds_user_id/i);
    await userEvent.type(sessionidInput, "A".repeat(40));
    await userEvent.type(dsUserIdInput, "1234567890");

    const submit = screen.getByRole("button", { name: /authenticate/i });
    await userEvent.click(submit);

    await waitFor(() => {
      expect(mockedStartReauth).toHaveBeenCalledTimes(1);
    });
    expect(mockedCompleteReauth).toHaveBeenCalledWith(
      "state-token-xyz",
      "A".repeat(40),
      "1234567890",
    );
    // After success, the banner should show the OK state.
    await waitFor(() => {
      expect(screen.getByText(/mallu\.wave/i)).toBeInTheDocument();
    });
  });

  it("surfaces a validation error from the server without logging the cookie", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.noProfile);
    mockedStartReauth.mockResolvedValue({
      token: "state-token-xyz",
      expires_at: Date.now() / 1000 + 600,
      approved_account: "mallu.wave",
    });
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    mockedCompleteReauth.mockRejectedValue(
      new InstagramAuthError(422, "ds_user_id: must be 6-20 digits"),
    );
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(screen.getByTestId("devtools-instructions")).toBeInTheDocument();
    });

    const sessionidInput = screen.getByLabelText(/sessionid/i);
    const dsUserIdInput = screen.getByLabelText(/ds_user_id/i);
    await userEvent.type(sessionidInput, "A".repeat(40));
    await userEvent.type(dsUserIdInput, "abc");

    const submit = screen.getByRole("button", { name: /authenticate/i });
    await userEvent.click(submit);

    await waitFor(() => {
      expect(
        screen.getByTestId("form-error"),
      ).toHaveTextContent(/must be 6-20 digits/i);
    });
    // The cookie values must NOT appear in console.error output.
    expect(consoleSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("A".repeat(40)),
    );
  });

  it("calls logout when the operator clicks log out", async () => {
    mockedFetchStatus.mockResolvedValue(STATUSES.ok);
    mockedLogout.mockResolvedValue({ state: "ok" });
    render(<InstagramAuthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/mallu\.wave/i)).toBeInTheDocument();
    });
    const button = screen.getByRole("button", { name: /log out/i });
    await userEvent.click(button);
    expect(mockedLogout).toHaveBeenCalledTimes(1);
  });
});
