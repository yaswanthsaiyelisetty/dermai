const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type User = { id: number; username: string };
export type AuthResponse = { access_token: string; token_type: string };
export type Case = {
  id: number;
  title: string;
  description: string | null;
  status: "open" | "in_progress" | "closed";
  created_at: string;
  updated_at: string;
  images: number | Array<Record<string, unknown>>;
};
export type UploadResult = {
  message: string;
  image: { filename: string; format: string; width: number; height: number; size_bytes: number };
};

function token(): string | null {
  return localStorage.getItem("dermai_access_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (token()) headers.set("Authorization", `Bearer ${token()}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "The request could not be completed.";
    throw new Error(detail);
  }
  return body as T;
}

export const api = {
  register: (username: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  cases: () => request<Case[]>("/cases"),
  createCase: (data: { title: string; description: string; status: string }) =>
    request<Case>("/cases", { method: "POST", body: JSON.stringify(data) }),
  getCase: (id: number) => request<Case>(`/cases/${id}`),
  updateCase: (id: number, data: Partial<Case>) =>
    request<Case>(`/cases/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCase: (id: number) => request<void>(`/cases/${id}`, { method: "DELETE" }),
  upload: (file: File, caseId?: number) => {
    const data = new FormData();
    data.append("file", file);
    const query = caseId ? `?case_id=${caseId}` : "";
    return request<UploadResult>(`/images/upload${query}`, { method: "POST", body: data });
  },
};
