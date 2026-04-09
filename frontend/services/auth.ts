const ACCESS_TOKEN_KEY = "adaptix-admin.access-token";
const ROLE_KEY = "adaptix-admin.role";
const TENANT_KEY = "adaptix-admin.tenant-id";
const USER_KEY = "adaptix-admin.user-id";
const API_BASE = process.env.NEXT_PUBLIC_ADMIN_API_BASE ?? "http://127.0.0.1:8012";

type LoginResponse = { access_token: string; role: string; tenant_id: string; user_id: string };

export function getStoredAuthToken() { return typeof window === "undefined" ? null : window.localStorage.getItem(ACCESS_TOKEN_KEY); }
export function getStoredAuthRole() { return typeof window === "undefined" ? "" : window.localStorage.getItem(ROLE_KEY) ?? ""; }
export function getStoredTenantId() { return typeof window === "undefined" ? "" : window.localStorage.getItem(TENANT_KEY) ?? ""; }
export function getStoredUserId() { return typeof window === "undefined" ? "" : window.localStorage.getItem(USER_KEY) ?? ""; }

export async function loginDev(payload: { role: string; tenant_id: string; user_id: string }) {
  const response = await fetch(`${API_BASE}/api/v1/auth/dev-login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error(await response.text() || `Login failed with ${response.status}`);
  const json = await response.json() as LoginResponse;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, json.access_token);
    window.localStorage.setItem(ROLE_KEY, json.role);
    window.localStorage.setItem(TENANT_KEY, json.tenant_id);
    window.localStorage.setItem(USER_KEY, json.user_id);
  }
  return json;
}

export function logout() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(ROLE_KEY);
  window.localStorage.removeItem(TENANT_KEY);
  window.localStorage.removeItem(USER_KEY);
}