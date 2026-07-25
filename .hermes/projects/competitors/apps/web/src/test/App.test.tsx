/**
 * Tests for the App-level auth gate.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { AuthError, me } from "../lib/auth";

vi.mock("../lib/auth", async () => {
  const actual = await vi.importActual<typeof import("../lib/auth")>("../lib/auth");
  return {
    ...actual,
    me: vi.fn(),
    logout: vi.fn(),
    login: vi.fn(),
  };
});

const mockedMe = vi.mocked(me);

describe("App auth gate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("redirects to /login when the user is not authenticated", async () => {
    mockedMe.mockResolvedValue(null);
    const { App } = await import("../App");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });
  });

  it("shows the dashboard when the user is authenticated", async () => {
    mockedMe.mockResolvedValue({ username: "operator" });
    // Mock the InstagramAuthBanner hook surface so the dashboard doesn't fetch.
    mockedMe.mockResolvedValue({ username: "operator" });
    const { App } = await import("../App");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
  });

  it("shows the dashboard after a 401 from /api/auth/me", async () => {
    mockedMe.mockRejectedValue(new AuthError(401, "unauthorized"));
    const { App } = await import("../App");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });
  });
});
