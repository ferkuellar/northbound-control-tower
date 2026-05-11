import type { TokenResponse, User } from "./types";

const TOKEN_KEY = "nct_access_token";
const USER_KEY = "nct_current_user";

const isBrowser = () => typeof window !== "undefined";

export function getToken(): string | null {
  if (!isBrowser()) {
    return null;
  }
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: TokenResponse): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(TOKEN_KEY, token.access_token);
}

export function clearSession(): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function setStoredUser(user: User): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getStoredUser(): User | null {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as User;
  } catch {
    window.localStorage.removeItem(USER_KEY);
    return null;
  }
}
