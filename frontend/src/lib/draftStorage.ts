// Remembers the reusable submission fields (name, age, place of living,
// country, gender) for the signed-in session. Persisted to localStorage so it
// survives navigation/refresh, and cleared on logout (see AuthContext).

import { type Gender } from "./apiClient";

const DRAFT_KEY = "submission_draft";

export type SubmissionDraft = {
  full_name: string;
  age: number | "";
  residence: string;
  country_of_origin: string;
  gender: Gender;
};

export const EMPTY_DRAFT: SubmissionDraft = {
  full_name: "",
  age: "",
  residence: "",
  country_of_origin: "",
  gender: "prefer_not_to_say",
};

export function loadSubmissionDraft(): SubmissionDraft {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? { ...EMPTY_DRAFT, ...JSON.parse(raw) } : { ...EMPTY_DRAFT };
  } catch {
    return { ...EMPTY_DRAFT };
  }
}

export function saveSubmissionDraft(draft: SubmissionDraft): void {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

export function clearSubmissionDraft(): void {
  localStorage.removeItem(DRAFT_KEY);
}
