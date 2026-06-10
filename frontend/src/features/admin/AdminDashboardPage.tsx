import { type FormEvent, useEffect, useState } from "react";

import { ErrorBanner } from "../../components/Banner";
import {
  apiClient,
  type PaginatedResponse,
  type SubmissionRecord,
} from "../../lib/apiClient";

type FilterState = {
  name: string;
  classificationLabel: string;
  countryOfOrigin: string;
  residence: string;
  gender: string;
  minAge: string;
  maxAge: string;
};

const EMPTY_FILTERS: FilterState = {
  name: "",
  classificationLabel: "",
  countryOfOrigin: "",
  residence: "",
  gender: "",
  minAge: "",
  maxAge: "",
};

const PAGE_SIZE = 20;

export default function AdminDashboardPage() {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageData, setPageData] = useState<PaginatedResponse<SubmissionRecord> | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function loadSubmissions(targetPage: number, activeFilters: FilterState) {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.searchSubmissions({
        name: activeFilters.name || undefined,
        classification_label: activeFilters.classificationLabel || undefined,
        country_of_origin: activeFilters.countryOfOrigin || undefined,
        residence: activeFilters.residence || undefined,
        gender: activeFilters.gender || undefined,
        min_age: activeFilters.minAge || undefined,
        max_age: activeFilters.maxAge || undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
      });
      setPageData(data);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadSubmissions(1, EMPTY_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    void loadSubmissions(1, filters);
  }

  function resetFilters() {
    setFilters(EMPTY_FILTERS);
    setPage(1);
    void loadSubmissions(1, EMPTY_FILTERS);
  }

  function goToPage(targetPage: number) {
    setPage(targetPage);
    void loadSubmissions(targetPage, filters);
  }

  const totalPages = pageData
    ? Math.max(1, Math.ceil(pageData.total / pageData.page_size))
    : 1;

  const updateFilter = (key: keyof FilterState) => (value: string) =>
    setFilters((current) => ({ ...current, [key]: value }));

  return (
    <div className="space-y-4">
      <div className="card">
        <h1 className="mb-4 text-xl font-semibold text-zinc-900">Admin · Submissions</h1>
        <form onSubmit={applyFilters} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="field-label">Name</label>
              <input
                className="input"
                value={filters.name}
                onChange={(event) => updateFilter("name")(event.target.value)}
              />
            </div>
            <div>
              <label className="field-label">Classification label</label>
              <input
                className="input"
                placeholder="e.g. balanced"
                value={filters.classificationLabel}
                onChange={(event) => updateFilter("classificationLabel")(event.target.value)}
              />
            </div>
            <div>
              <label className="field-label">Country of origin</label>
              <input
                className="input"
                value={filters.countryOfOrigin}
                onChange={(event) => updateFilter("countryOfOrigin")(event.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="field-label">Place of living</label>
              <input
                className="input"
                value={filters.residence}
                onChange={(event) => updateFilter("residence")(event.target.value)}
              />
            </div>
            <div>
              <label className="field-label">Gender</label>
              <select
                className="input"
                value={filters.gender}
                onChange={(event) => updateFilter("gender")(event.target.value)}
              >
                <option value="">Any</option>
                <option value="male">male</option>
                <option value="female">female</option>
                <option value="other">other</option>
                <option value="prefer_not_to_say">prefer not to say</option>
              </select>
            </div>
            <div>
              <label className="field-label">Min age</label>
              <input
                type="number"
                min={0}
                className="input"
                value={filters.minAge}
                onChange={(event) => updateFilter("minAge")(event.target.value)}
              />
            </div>
            <div>
              <label className="field-label">Max age</label>
              <input
                type="number"
                min={0}
                className="input"
                value={filters.maxAge}
                onChange={(event) => updateFilter("maxAge")(event.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? "Searching…" : "Apply filters"}
            </button>
            <button type="button" className="btn-ghost" onClick={resetFilters}>
              Reset
            </button>
          </div>
        </form>
      </div>

      {errorMessage && <ErrorBanner message={errorMessage} />}

      {pageData && (
        <div className="card">
          <p className="mb-3 text-sm text-zinc-500">
            {pageData.total} result(s) · page {pageData.page} / {totalPages}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500">
                  <th className="py-2 pr-3 font-medium">Photo</th>
                  <th className="py-2 pr-3 font-medium">Name</th>
                  <th className="py-2 pr-3 font-medium">Age</th>
                  <th className="py-2 pr-3 font-medium">Gender</th>
                  <th className="py-2 pr-3 font-medium">Country</th>
                  <th className="py-2 pr-3 font-medium">Lives in</th>
                  <th className="py-2 pr-3 font-medium">Label</th>
                  <th className="py-2 pr-3 font-medium">Score</th>
                  <th className="py-2 pr-3 font-medium">Submitted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {pageData.items.map((submission) => (
                  <tr key={submission.id} className="text-zinc-700">
                    <td className="py-2 pr-3">
                      <a href={submission.photo_url} target="_blank" rel="noreferrer">
                        <img
                          src={submission.photo_url}
                          alt={submission.full_name}
                          className="h-12 w-12 rounded-lg object-cover"
                        />
                      </a>
                    </td>
                    <td className="py-2 pr-3 font-medium text-zinc-900">{submission.full_name}</td>
                    <td className="py-2 pr-3">{submission.age}</td>
                    <td className="py-2 pr-3">{submission.gender}</td>
                    <td className="py-2 pr-3">{submission.country_of_origin}</td>
                    <td className="py-2 pr-3">{submission.residence}</td>
                    <td className="py-2 pr-3">
                      <span className="badge-brand">{submission.classification_label}</span>
                    </td>
                    <td className="py-2 pr-3">{submission.classification_score}/100</td>
                    <td className="py-2 pr-3 text-zinc-500">
                      {new Date(submission.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="btn-ghost"
              disabled={isLoading || page <= 1}
              onClick={() => goToPage(page - 1)}
            >
              ← Prev
            </button>
            <button
              type="button"
              className="btn-ghost"
              disabled={isLoading || page >= totalPages}
              onClick={() => goToPage(page + 1)}
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
