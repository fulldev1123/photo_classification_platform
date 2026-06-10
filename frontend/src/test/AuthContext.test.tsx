import { act, render, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type ReactNode } from "react";

import { AuthProvider, useAuth } from "../context/AuthContext";

// Mock only the network surface; keep the real token storage helpers so the
// tests can assert against localStorage behaviour.
vi.mock("../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/apiClient")>();
  return {
    ...actual,
    apiClient: {
      currentAccount: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
    },
  };
});

import { apiClient, readStoredToken, storeToken } from "../lib/apiClient";

const mocked = vi.mocked(apiClient);

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("starts unauthenticated when there is no token", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.account).toBeNull();
    expect(mocked.currentAccount).not.toHaveBeenCalled();
  });

  it("loads the account when a token is present", async () => {
    storeToken("abc");
    mocked.currentAccount.mockResolvedValueOnce({
      id: "u1",
      email: "alice@example.com",
      is_admin: true,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.account).toEqual({
      id: "u1",
      email: "alice@example.com",
      is_admin: true,
    });
  });

  it("clears the token when /auth/me fails (expired/invalid)", async () => {
    storeToken("stale");
    mocked.currentAccount.mockRejectedValueOnce(new Error("401"));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.account).toBeNull();
    expect(readStoredToken()).toBeNull();
  });

  it("login() stores the token and loads the account", async () => {
    mocked.login.mockResolvedValueOnce({ access_token: "fresh", expires_in: 3600 });
    mocked.currentAccount.mockResolvedValueOnce({
      id: "u2",
      email: "bob@example.com",
      is_admin: false,
      is_active: true,
      created_at: "",
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login("bob@example.com", "pw");
    });

    expect(readStoredToken()).toBe("fresh");
    expect(result.current.account?.email).toBe("bob@example.com");
  });

  it("logout() clears the token and the account", async () => {
    storeToken("abc");
    mocked.currentAccount.mockResolvedValueOnce({
      id: "u1",
      email: "a@b.c",
      is_admin: false,
      is_active: true,
      created_at: "",
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.account).not.toBeNull());

    act(() => {
      result.current.logout();
    });

    expect(result.current.account).toBeNull();
    expect(readStoredToken()).toBeNull();
  });

  it("throws when useAuth is used outside the provider", () => {
    const Orphan = () => {
      useAuth();
      return null;
    };
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Orphan />)).toThrow(/AuthProvider/);
    spy.mockRestore();
  });
});
