import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../../components/Banner";
import { useAuth } from "../../context/AuthContext";
import { apiClient } from "../../lib/apiClient";

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await apiClient.register(email, password);
      await login(email, password);
      navigate("/submit");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-md">
      <div className="card">
        <h1 className="mb-1 text-xl font-semibold text-zinc-900">Create your account</h1>
        <p className="mb-6 text-sm text-zinc-500">It only takes a moment to get started.</p>
        {errorMessage && <ErrorBanner message={errorMessage} />}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="field-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="password">
              Password <span className="text-zinc-400">(min 8 characters)</span>
            </label>
            <input
              id="password"
              type="password"
              minLength={8}
              className="input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account…" : "Register"}
          </button>
        </form>
        <p className="mt-4 text-sm text-zinc-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
