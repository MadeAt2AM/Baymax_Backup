/**
 * Tests for the auth context.
 *
 * The auth context is the single source of truth for the dashboard's
 * "is the user signed in?" question. The App component reads from it
 * to decide which routes to render. These tests cover the three
 * transitions that matter:
 *
 *   1. Initial mount: fetch /api/auth/me.
 *   2. signIn: on success, auth flips to "authenticated".
 *   3. signOut: auth flips back to "anonymous".
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AuthError } from "../lib/auth";

vi.mock("../lib/auth", async () => {
  const actual = await vi.importActual<typeof import("../lib/auth")>("../lib/auth");
  return {
    ...actual,
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  };
});

import { AuthProvider, useAuth } from "../lib/auth-context";
import { login, logout, me } from "../lib/auth";

const mockedMe = vi.mocked(me);
const mockedLogin = vi.mocked(login);
const mockedLogout = vi.mocked(logout);

function AuthProbe() {
  const { auth, username, signIn, signOut } = useAuth();
  return (
    <div>
      <p data-testid="auth">{auth}</p>
      <p data-testid="username">{username ?? "(none)"}</p>
      <button
        type="button"
        onClick={() => {
          void signIn("operator", "Test123!");
        }}
      >
        sign in
      </button>
      <button
        type="button"
        onClick={() => {
          void signOut();
        }}
      >
        sign out
      </button>
    </div>
  );
}

function renderProbe() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Routes>
          <Route path="*" element={<AuthProbe />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("auth context", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts in loading, then becomes anonymous when /me returns null", async () => {
    mockedMe.mockResolvedValue(null);
    renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("anonymous");
    });
    expect(screen.getByTestId("username")).toHaveTextContent("(none)");
  });

  it("starts in loading, then becomes authenticated when /me returns a user", async () => {
    mockedMe.mockResolvedValue({ username: "operator" });
    renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("authenticated");
    });
    expect(screen.getByTestId("username")).toHaveTextContent("operator");
  });

  it("falls back to anonymous when /me rejects with AuthError(401)", async () => {
    mockedMe.mockRejectedValue(new AuthError(401, "unauthorized"));
    renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("anonymous");
    });
  });

  it("signIn flips auth to authenticated on success", async () => {
    mockedMe.mockResolvedValue(null);
    mockedLogin.mockResolvedValue({ username: "operator" });
    renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("anonymous");
    });

    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("authenticated");
    });
    expect(screen.getByTestId("username")).toHaveTextContent("operator");
  });

  it("signOut flips auth back to anonymous", async () => {
    mockedMe.mockResolvedValue({ username: "operator" });
    mockedLogout.mockResolvedValue();
    renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("authenticated");
    });

    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: /sign out/i }));
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth")).toHaveTextContent("anonymous");
    });
  });
});
