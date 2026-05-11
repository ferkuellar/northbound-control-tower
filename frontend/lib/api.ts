import type {
  CloudAccount,
  FindingListResponse,
  FindingSummary,
  Resource,
  ScoreHistoryResponse,
  ScoreLatestResponse,
  ScoreSummary,
  TokenResponse,
  User,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiFetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  token?: string | null;
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildUrl(path: string, query?: ApiFetchOptions["query"]): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

function errorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  if (typeof payload === "object" && payload !== null && "error" in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string") {
      return error;
    }
  }
  return fallback;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers = new Headers({ Accept: "application/json" });

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    throw new ApiError(errorMessage(payload, "Request failed"), response.status);
  }

  return payload as T;
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function getCurrentUser(token: string): Promise<User> {
  return apiFetch<User>("/api/v1/auth/me", { token });
}

export function getResources(token: string): Promise<Resource[]> {
  return apiFetch<Resource[]>("/api/v1/resources", { token });
}

export function getFindings(token: string): Promise<FindingListResponse> {
  return apiFetch<FindingListResponse>("/api/v1/findings", { token });
}

export function getFindingsSummary(token: string): Promise<FindingSummary> {
  return apiFetch<FindingSummary>("/api/v1/findings/summary", { token });
}

export function getScoresLatest(token: string): Promise<ScoreLatestResponse> {
  return apiFetch<ScoreLatestResponse>("/api/v1/scores/latest", { token });
}

export function getScoresSummary(token: string): Promise<ScoreSummary> {
  return apiFetch<ScoreSummary>("/api/v1/scores/summary", { token });
}

export function getScoreHistory(token: string): Promise<ScoreHistoryResponse> {
  return apiFetch<ScoreHistoryResponse>("/api/v1/scores/history", {
    token,
    query: { limit: 100 },
  });
}

export function getCloudAccounts(token: string): Promise<CloudAccount[]> {
  return apiFetch<CloudAccount[]>("/api/v1/cloud-accounts", { token });
}
