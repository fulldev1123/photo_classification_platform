import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

type RequireAuthProps = {
  children: JSX.Element;
  adminOnly?: boolean;
};

export default function RequireAuth({ children, adminOnly = false }: RequireAuthProps) {
  const { account, isLoading } = useAuth();
  if (isLoading) {
    return <div className="p-8 text-center text-zinc-500">Loading…</div>;
  }
  if (!account) return <Navigate to="/login" replace />;
  if (adminOnly && !account.is_admin) return <Navigate to="/submit" replace />;
  return children;
}
