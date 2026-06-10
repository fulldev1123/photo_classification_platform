// Thin fetch wrapper around the two backend services. It centralizes
// bearer-token wiring and converts non-2xx responses into readable Errors so
// callers can surface `error.message` directly.

const AUTH_API = import.meta.env.VITE_AUTH_API || "http://localhost:8001";
const SUBMISSION_API = import.meta.env.VITE_SUBMISSION_API || "http://localhost:8002";

export const apiBaseUrls = { auth: AUTH_API, submission: SUBMISSION_API };

export type Gender = "male" | "female" | "other" | "prefer_not_to_say";

export type SubmissionRecord = {
  id: string;
  owner_id: string;
  full_name: string;
  age: number;
  residence: string;
  gender: Gender;
  country_of_origin: string;
  description: string | null;
  photo_key: string;
  photo_content_type: string;
  photo_size_bytes: number;
  classification_label: string;
  classification_score: number;
  classification_meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  photo_url: string;
};

export type Account = {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type SubmissionQuery = Record<string, string | number | undefined>;

const TOKEN_STORAGE_KEY = "photo_platform_token";

export function readStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body?.detail) {
      return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    /* response body was not JSON */
  }
  return `${response.status} ${response.statusText}`;
}

async function httpRequest<T>(
  baseUrl: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const token = readStoredToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  // The browser sets the multipart boundary for FormData itself, so only force
  // JSON on non-FormData bodies.
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const apiClient = {
  register(email: string, password: string) {
    return httpRequest<{ id: string; email: string }>(AUTH_API, "/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  login(email: string, password: string) {
    return httpRequest<{ access_token: string; expires_in: number }>(
      AUTH_API,
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    );
  },
  currentAccount() {
    return httpRequest<Account>(AUTH_API, "/auth/me");
  },
  createSubmission(form: FormData) {
    return httpRequest<SubmissionRecord>(SUBMISSION_API, "/submissions", {
      method: "POST",
      body: form,
    });
  },
  mySubmissions() {
    return httpRequest<SubmissionRecord[]>(SUBMISSION_API, "/submissions/me");
  },
  searchSubmissions(query: SubmissionQuery) {
    const search = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    return httpRequest<PaginatedResponse<SubmissionRecord>>(
      SUBMISSION_API,
      `/admin/submissions?${search.toString()}`,
    );
  },
};
