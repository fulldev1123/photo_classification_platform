import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  apiClient,
  clearStoredToken,
  readStoredToken,
  storeToken,
} from "../lib/apiClient";

export type AuthenticatedAccount = {
  id: string;
  email: string;
  is_admin: boolean;
};

type AuthContextValue = {
  account: AuthenticatedAccount | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  reloadAccount: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<AuthenticatedAccount | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const reloadAccount = useCallback(async () => {
    if (!readStoredToken()) {
      setAccount(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await apiClient.currentAccount();
      setAccount({ id: me.id, email: me.email, is_admin: me.is_admin });
    } catch {
      clearStoredToken();
      setAccount(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void reloadAccount();
  }, [reloadAccount]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await apiClient.login(email, password);
      storeToken(access_token);
      await reloadAccount();
    },
    [reloadAccount],
  );

  const logout = useCallback(() => {
    clearStoredToken();
    setAccount(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ account, isLoading, login, logout, reloadAccount }),
    [account, isLoading, login, logout, reloadAccount],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
