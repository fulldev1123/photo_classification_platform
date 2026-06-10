import { useEffect, useState } from "react";

import { ErrorBanner } from "../../components/Banner";
import { apiClient, type SubmissionRecord } from "../../lib/apiClient";

export default function MySubmissionsPage() {
  const [submissions, setSubmissions] = useState<SubmissionRecord[] | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .mySubmissions()
      .then(setSubmissions)
      .catch((error: unknown) =>
        setErrorMessage(error instanceof Error ? error.message : String(error)),
      );
  }, []);

  if (errorMessage) return <ErrorBanner message={errorMessage} />;
  if (!submissions) return <div className="p-8 text-center text-zinc-500">Loading…</div>;
  if (submissions.length === 0) {
    return (
      <div className="card text-sm text-zinc-500">
        You haven&apos;t submitted any submissions yet.
      </div>
    );
  }

  return (
    <div className="card">
      <h1 className="mb-4 text-xl font-semibold text-zinc-900">My submissions</h1>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">Photo</th>
              <th className="py-2 pr-3 font-medium">Name</th>
              <th className="py-2 pr-3 font-medium">Age</th>
              <th className="py-2 pr-3 font-medium">Country</th>
              <th className="py-2 pr-3 font-medium">Classification</th>
              <th className="py-2 pr-3 font-medium">Score</th>
              <th className="py-2 pr-3 font-medium">Submitted</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {submissions.map((submission) => (
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
                <td className="py-2 pr-3">{submission.country_of_origin}</td>
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
    </div>
  );
}
