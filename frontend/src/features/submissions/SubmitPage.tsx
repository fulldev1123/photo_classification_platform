import { type FormEvent, useState } from "react";

import { ErrorBanner, SuccessBanner } from "../../components/Banner";
import { apiClient, type Gender, type SubmissionRecord } from "../../lib/apiClient";

const GENDER_OPTIONS: Gender[] = ["male", "female", "other", "prefer_not_to_say"];

const humanize = (value: string) => value.replace(/_/g, " ");

export default function SubmitPage() {
  const [fullName, setFullName] = useState("");
  const [age, setAge] = useState<number | "">("");
  const [residence, setResidence] = useState("");
  const [gender, setGender] = useState<Gender>("prefer_not_to_say");
  const [countryOfOrigin, setCountryOfOrigin] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<SubmissionRecord | null>(null);

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
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="card">
        <h1 className="mb-1 text-xl font-semibold text-zinc-900">New submission</h1>
        <p className="mb-6 text-sm text-zinc-500">
          Upload a photo with a few details. We classify it on submission.
        </p>
        {errorMessage && <ErrorBanner message={errorMessage} />}
        <form onSubmit={handleSubmit} className="space-y-4">
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

          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Uploading…" : "Submit submission"}
          </button>
        </form>
      </div>

      {result && (
        <div className="card">
          <SuccessBanner>
            Submitted. Classification:{" "}
            <strong className="font-semibold">{result.classification_label}</strong> (confidence{" "}
            {result.classification_score}/100)
          </SuccessBanner>
          <img
            src={result.photo_url}
            alt={result.full_name}
            className="h-40 w-40 rounded-xl object-cover"
          />
        </div>
      )}
    </div>
  );
}
