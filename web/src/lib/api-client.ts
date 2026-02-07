const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function getApiKey(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|; )wybe_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const key = getApiKey();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (key) {
    headers["Authorization"] = `Bearer ${key}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  del(path: string): Promise<void> {
    return request<void>(path, { method: "DELETE" });
  },
};
