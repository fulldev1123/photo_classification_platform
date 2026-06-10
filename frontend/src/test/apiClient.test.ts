import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient, storeToken } from "../lib/apiClient";

type FetchInit = RequestInit & { headers?: Headers };

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("apiClient", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("attaches the Bearer token from storage", async () => {
    storeToken("tok-123");
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "u1", email: "a@b.c", is_admin: false, is_active: true, created_at: "" }),
    );

    await apiClient.currentAccount();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0][1] as FetchInit;
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer tok-123");
  });

  it("does not attach Authorization when there is no token", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ access_token: "x", expires_in: 60 }));

    await apiClient.login("a@b.c", "pw");

    const init = fetchMock.mock.calls[0][1] as FetchInit;
    expect((init.headers as Headers).get("Authorization")).toBeNull();
    expect((init.headers as Headers).get("Content-Type")).toBe("application/json");
  });

  it("throws with the API detail on non-2xx responses", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid credentials" }), {
        status: 401,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiClient.login("a@b.c", "wrong")).rejects.toThrow("Invalid credentials");
  });

  it("falls back to the status text when the body is not JSON", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("oops", { status: 500, statusText: "Internal Server Error" }),
    );

    await expect(apiClient.currentAccount()).rejects.toThrow(/500/);
  });

  it("does not set Content-Type for FormData uploads", async () => {
    storeToken("tok-xyz");
    fetchMock.mockResolvedValueOnce(jsonResponse({ id: "p1" }));

    const form = new FormData();
    form.append("full_name", "test");
    await apiClient.createSubmission(form);

    const init = fetchMock.mock.calls[0][1] as FetchInit;
    // The browser must set Content-Type itself to include the multipart boundary.
    expect((init.headers as Headers).get("Content-Type")).toBeNull();
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer tok-xyz");
  });

  it("serialises admin filters into the query string", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ items: [], total: 0, page: 1, page_size: 20 }),
    );

    await apiClient.searchSubmissions({
      name: "alice",
      classification_label: "balanced",
      empty: "",
      undef: undefined,
      page: 2,
    });

    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("/admin/submissions?");
    expect(url).toContain("name=alice");
    expect(url).toContain("classification_label=balanced");
    expect(url).toContain("page=2");
    expect(url).not.toContain("empty=");
    expect(url).not.toContain("undef=");
  });
});
