import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const LINK_BASE = "rounded-lg px-3 py-1.5 text-sm font-medium transition";

export default function NavBar() {
  const { account, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const navLinkClass = (path: string) =>
    `${LINK_BASE} ${
      pathname === path
        ? "bg-brand-50 text-brand-700"
        : "text-zinc-600 hover:bg-zinc-100"
    }`;

  return (
    <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-3">
        <Link to="/" className="mr-2 flex items-center gap-2 font-semibold text-zinc-900">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white">
            P
          </span>
          Photo Platform
        </Link>

        {account && (
          <>
            <Link to="/submit" className={navLinkClass("/submit")}>
              Submit
            </Link>
            <Link to="/me" className={navLinkClass("/me")}>
              My submissions
            </Link>
            {account.is_admin && (
              <Link to="/admin" className={navLinkClass("/admin")}>
                Admin
              </Link>
            )}
          </>
        )}

        <div className="flex-1" />

        {account ? (
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-zinc-500 sm:inline">{account.email}</span>
            {account.is_admin && <span className="badge-brand">admin</span>}
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link to="/login" className={navLinkClass("/login")}>
              Login
            </Link>
            <Link to="/register" className="btn-primary">
              Register
            </Link>
          </div>
        )}
      </nav>
    </header>
  );
}
