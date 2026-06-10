import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "../features/auth/LoginPage";

const loginMock = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    account: null,
    isLoading: false,
    login: loginMock,
    logout: vi.fn(),
    reloadAccount: vi.fn(),
  }),
}));

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/submit" element={<div>Submit page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("submits credentials and navigates to /submit on success", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();

    const { container } = renderLoginPage();

    const email = container.querySelector<HTMLInputElement>("input[type=email]")!;
    const password = container.querySelector<HTMLInputElement>("input[type=password]")!;

    await user.clear(email);
    await user.type(email, "alice@example.com");
    await user.clear(password);
    await user.type(password, "secret-password");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    expect(loginMock).toHaveBeenCalledWith("alice@example.com", "secret-password");
    await waitFor(() => {
      expect(screen.getByText("Submit page")).toBeInTheDocument();
    });
  });

  it("renders the API error message on failed login", async () => {
    loginMock.mockRejectedValueOnce(new Error("Invalid credentials"));
    const user = userEvent.setup();

    renderLoginPage();

    await user.click(screen.getByRole("button", { name: /log in/i }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });
});
