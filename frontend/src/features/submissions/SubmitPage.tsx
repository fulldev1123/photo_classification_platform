import { type FormEvent, useEffect, useMemo, useState } from "react";

import { ErrorBanner, SuccessBanner } from "../../components/Banner";
import { apiClient, type Gender, type SubmissionRecord } from "../../lib/apiClient";
import { loadSubmissionDraft, saveSubmissionDraft } from "../../lib/draftStorage";

const GENDER_OPTIONS: Gender[] = ["male", "female", "other", "prefer_not_to_say"];

const humanize = (value: string) => value.replace(/_/g, " ");

export default function SubmitPage() {
  // Reusable fields are restored from the session draft (cleared on logout).
  const draft = useMemo(() => loadSubmissionDraft(), []);
  const [fullName, setFullName] = useState(draft.full_name);
  const [age, setAge] = useState<number | "">(draft.age);
  const [residence, setResidence] = useState(draft.residence);
  const [gender, setGender] = useState<Gender>(draft.gender);
  const [countryOfOrigin, setCountryOfOrigin] = useState(draft.country_of_origin);
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<SubmissionRecord | null>(null);

  // Keep the reusable fields in the session draft as they change.
  useEffect(() => {
    saveSubmissionDraft({
      full_name: fullName,
      age,
      residence,
      country_of_origin: countryOfOrigin,
      gender,
    });
  }, [fullName, age, residence, countryOfOrigin, gender]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!photo) {
      setErrorMessage("Please choose a photo.");
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("full_name", fullName);
      form.append("age", String(age));
      form.append("residence", residence);
      form.append("gender", gender);
      form.append("country_of_origin", countryOfOrigin);
      if (description) form.append("description", description);
      form.append("photo", photo);
      setResult(await apiClient.createSubmission(form));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
        {/* Left: the submission form */}
        <div className="card">
          <h1 className="mb-1 text-xl font-semibold text-zinc-900">New submission</h1>
          <p className="mb-6 text-sm text-zinc-500">
            Upload a photo with a few details. We classify it on submission.
          </p>
          {errorMessage && <ErrorBanner message={errorMessage} />}
          <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="full_name">
                  Full name
                </label>
                <input
                  id="full_name"
                  className="input"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="age">
                  Age
                </label>
                <input
                  id="age"
                  type="number"
                  min={0}
                  max={130}
                  className="input"
                  value={age}
                  onChange={(event) =>
                    setAge(event.target.value === "" ? "" : Number(event.target.value))
                  }
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="residence">
                  Place of living
                </label>
                <input
                  id="residence"
                  className="input"
                  value={residence}
                  onChange={(event) => setResidence(event.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="country_of_origin">
                  Country of origin
                </label>
                <input
                  id="country_of_origin"
                  className="input"
                  value={countryOfOrigin}
                  onChange={(event) => setCountryOfOrigin(event.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label className="field-label" htmlFor="gender">
                Gender
              </label>
              <select
                id="gender"
                className="input"
                value={gender}
                onChange={(event) => setGender(event.target.value as Gender)}
              >
                {GENDER_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {humanize(option)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label" htmlFor="description">
                Description <span className="text-zinc-400">(optional)</span>
              </label>
              <textarea
                id="description"
                className="input min-h-24 resize-y"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>

            <div>
              <label className="field-label" htmlFor="photo">
                Photo <span className="text-zinc-400">(jpg / png / webp, max 5 MB)</span>
              </label>
              <input
                id="photo"
                type="file"
                accept="image/*"
                className="block w-full text-sm text-zinc-600 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-brand-700 hover:file:bg-brand-100"
                onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
                required
              />
            </div>

            <button type="submit" className="ml-auto btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Submitting…" : "Submit"}
            </button>
          </form>
        </div>

        {/* Right: the classification result */}
        <div className="lg:sticky lg:top-20">
          {result ? (
            <div className="card">
              <SuccessBanner>Submission created.</SuccessBanner>
              <img
                src={result.photo_url}
                alt={result.full_name}
                className="mb-4 h-48 w-full rounded-xl object-cover"
              />
              <dl className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-zinc-500">Classification</dt>
                  <dd>
                    <span className="badge-brand">{result.classification_label}</span>
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-zinc-500">Confidence</dt>
                  <dd className="font-medium text-zinc-800">
                    {result.classification_score}/100
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-zinc-500">Name</dt>
                  <dd className="font-medium text-zinc-800">{result.full_name}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <div className="card border-dashed">
              <h2 className="mb-1 text-base font-semibold text-zinc-700">Result</h2>
              <p className="text-sm text-zinc-500">
                Your classification result will appear here after you submit.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
