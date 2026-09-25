import { getUserId } from "./session";
import type { QuizQuestion } from "./quiz";
import { MAX_FIELDS } from "./types";
import type {
  AuthResult,
  ConsentBody,
  LegalInfo,
  CapabilityKind,
  CapabilityRef,
  CompanyDetail,
  CompanyOut,
  Domain,
  Feed,
  JD,
  JDBody,
  JDGaps,
  Lens,
  NamedRef,
  OnboardingBody,
  PlacementBody,
  PlacementResult,
  Profile,
  Pulse,
  RoleDetail,
  RoleRef,
  SavedItem,
  SearchResults,
  SkillGaps,
  Streak,
  TargetsBody,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function messageFrom(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "unknown_ids" in detail) {
    return "Something you picked isn't available any more. Pick it again.";
  }
  if (Array.isArray(detail)) {
    const fields = detail.find((d) => Array.isArray(d?.loc) && d.loc.includes("domain_ids") && d.type === "too_long");
    if (fields) return `You can follow up to ${MAX_FIELDS} fields. Remove one to add another.`;
    const short = detail.find((d) => Array.isArray(d?.loc) && d.loc.includes("text") && d.type === "string_too_short");
    if (short) return "That's too short to be a job description. Paste the full text.";
    return "Some of that input isn't valid.";
  }
  return status >= 500 ? "Something broke on our side. Try again in a moment." : "That didn't work.";
}

interface Options {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: Options = {}): Promise<T> {
  try {
    return await send<T>(path, options);
  } catch (error) {
    // A reused connection can be closed by the server just as it is picked up, which the proxy reports as a 5xx.
    // Reads are safe to repeat once; writes are never retried.
    const retryable = (options.method ?? "GET") === "GET" && error instanceof ApiError && error.status >= 500;
    if (!retryable || options.signal?.aborted) throw error;
    await new Promise((resolve) => setTimeout(resolve, 250));
    return send<T>(path, options);
  }
}

async function send<T>(path: string, { method = "GET", body, signal }: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const userId = getUserId();
  if (userId) headers["X-User-Id"] = userId;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "You're offline, or the server can't be reached.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(response.status, messageFrom(payload?.detail, response.status));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function download(path: string): Promise<Blob> {
  const headers: Record<string, string> = {};
  const userId = getUserId();
  if (userId) headers["X-User-Id"] = userId;
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { headers, cache: "no-store" });
  } catch {
    throw new ApiError(0, "You're offline, or the server can't be reached.");
  }
  if (!response.ok) throw new ApiError(response.status, "Couldn't prepare your data. Try again in a moment.");
  return response.blob();
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "" && value !== false) search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
};

export const api = {
  signup: (email: string, password: string, consent: ConsentBody) =>
    request<AuthResult>("/auth/signup", { method: "POST", body: { email, password, consent } }),
  legal: (signal?: AbortSignal) => request<LegalInfo>("/public/legal", { signal }),
  deleteAccount: (password?: string) =>
    request<void>("/privacy/account", { method: "DELETE", body: { password: password ?? null } }),
  /** The JSON file of everything held about the reader, as a Blob to save. */
  exportData: () => download("/privacy/export"),
  login: (email: string, password: string) => request<AuthResult>("/auth/login", { method: "POST", body: { email, password } }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: (signal?: AbortSignal) => request<AuthResult>("/auth/me", { signal }),
  pulse: (signal?: AbortSignal) => request<Pulse>("/public/pulse", { signal }),

  onboard: (body: OnboardingBody) => request<Profile>("/onboarding", { method: "POST", body }),
  profile: (userId: string, signal?: AbortSignal) => request<Profile>(`/profile/${userId}`, { signal }),
  putTargets: (userId: string, body: TargetsBody) =>
    request<Profile>(`/profile/${userId}/targets`, { method: "PUT", body }),
  placement: (userId: string, body: PlacementBody) =>
    request<PlacementResult>(`/profile/${userId}/placement`, { method: "POST", body }),
  skillGaps: (userId: string, signal?: AbortSignal) => request<SkillGaps>(`/profile/${userId}/skill-gaps`, { signal }),
  feed: (userId: string, lens: Lens, offset: number, domainId?: string | null, signal?: AbortSignal) =>
    request<Feed>(`/feed/${userId}${qs({ lens, offset, limit: 20, domain_id: domainId })}`, { signal }),
  interact: (userId: string, articleId: string, action: "save" | "unsave" | "dismiss" | "undismiss" | "read") =>
    request<{ article_id: string; saved: boolean; dismissed: boolean }>(`/feed/${userId}/interaction`, {
      method: "POST",
      body: { article_id: articleId, action },
    }),
  saved: (userId: string, signal?: AbortSignal) => request<SavedItem[]>(`/feed/${userId}/saved`, { signal }),
  streak: (userId: string, signal?: AbortSignal) => request<Streak>(`/streaks/${userId}`, { signal }),
  touchStreak: (userId: string) => request<Streak>(`/streaks/${userId}/touch`, { method: "POST" }),
  quiz: (userId: string, level: number, exclude: string[], count: number, signal?: AbortSignal) =>
    request<{ level: number; questions: QuizQuestion[] }>(`/quiz/${userId}${qs({ level, count, exclude: exclude.join(",") })}`, { signal }),

  domains: (signal?: AbortSignal) => request<Domain[]>("/taxonomy/domains", { signal }),
  roles: (q: string, domainId?: string | null, signal?: AbortSignal, limit = 40, mba = false) =>
    request<RoleRef[]>(`/taxonomy/roles${qs({ q, domain_id: domainId, limit, mba })}`, { signal }),
  roleDetail: (id: string, signal?: AbortSignal) => request<RoleDetail>(`/taxonomy/roles/${id}`, { signal }),
  companies: (q: string, domainId?: string | null, signal?: AbortSignal, limit = 40, mba = false) =>
    request<CompanyOut[]>(`/taxonomy/companies${qs({ q, domain_id: domainId, limit, mba })}`, { signal }),
  companyDetail: (id: string, signal?: AbortSignal) => request<CompanyDetail>(`/taxonomy/companies/${id}`, { signal }),
  industries: (signal?: AbortSignal) => request<NamedRef[]>("/taxonomy/industries", { signal }),
  capabilities: (q: string, domainId?: string | null, kind?: CapabilityKind, signal?: AbortSignal, limit = 40, mba = false) =>
    request<CapabilityRef[]>(`/taxonomy/capabilities${qs({ q, kind, domain_id: domainId, limit, mba })}`, { signal }),

  jds: (userId: string, signal?: AbortSignal) => request<JD[]>(`/jds/${userId}`, { signal }),
  jdGaps: (userId: string, signal?: AbortSignal) => request<JDGaps>(`/jds/${userId}/gaps`, { signal }),
  addJd: (userId: string, body: JDBody) => request<JD>(`/jds/${userId}`, { method: "POST", body }),
  patchJd: (userId: string, id: string, body: Partial<Omit<JDBody, "text">>) =>
    request<JD>(`/jds/${userId}/${id}`, { method: "PATCH", body }),
  deleteJd: (userId: string, id: string) => request<void>(`/jds/${userId}/${id}`, { method: "DELETE" }),
  search: (q: string, signal?: AbortSignal) =>
    request<SearchResults>(`/taxonomy/search${qs({ q })}`, { signal }),
};
