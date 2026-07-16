import type {
  AnalyticsChatDetail,
  AnalyticsChatsPage,
  AnalyticsOverview,
  AnalyticsOwner,
  AnalyticsPath,
  ChatGroup,
  ChatSummary,
  ErrorsResult,
  Me,
  ModelsResult,
  StoredMessage,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { credentials: "include", ...init });
  if (!r.ok) throw new ApiError(r.status, `${init?.method ?? "GET"} ${url} -> ${r.status}`);
  return (await r.json()) as T;
}

const jsonHeaders = { "Content-Type": "application/json" };

export async function me(): Promise<Me | null> {
  const r = await fetch("/api/auth/me", { credentials: "include" });
  return r.ok ? ((await r.json()) as Me) : null;
}

export function listChats(status?: string): Promise<ChatSummary[]> {
  return json<ChatSummary[]>("/api/chats" + (status ? `?status=${status}` : ""));
}

export function createChat(title = "Nuova chat"): Promise<ChatSummary> {
  return json<ChatSummary>("/api/chats", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ title }),
  });
}

export function getChat(id: number): Promise<ChatSummary> {
  return json<ChatSummary>(`/api/chats/${id}`);
}

export function patchChat(id: number, body: { title?: string }): Promise<ChatSummary> {
  return json<ChatSummary>(`/api/chats/${id}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  });
}

export function getMessages(id: number): Promise<StoredMessage[]> {
  return json<StoredMessage[]>(`/api/chats/${id}/messages`);
}

export async function deleteChat(id: number): Promise<void> {
  const r = await fetch(`/api/chats/${id}`, { method: "DELETE", credentials: "include" });
  if (!r.ok) throw new ApiError(r.status, `DELETE /api/chats/${id} -> ${r.status}`);
}

export function setChatStatus(id: number, status: "active" | "archived" | "trashed"): Promise<ChatSummary> {
  return json<ChatSummary>(`/api/chats/${id}`, { method: "PATCH", headers: jsonHeaders, body: JSON.stringify({ status }) });
}

export function moveChatToGroup(id: number, chat_group_id: number | null): Promise<ChatSummary> {
  return json<ChatSummary>(`/api/chats/${id}`, { method: "PATCH", headers: jsonHeaders, body: JSON.stringify({ chat_group_id }) });
}

export async function shareChat(id: number, email: string, permission: "read" | "write"): Promise<void> {
  const r = await fetch(`/api/chats/${id}/share`, {
    method: "POST", headers: jsonHeaders, credentials: "include", body: JSON.stringify({ email, permission }),
  });
  if (!r.ok) throw new ApiError(r.status, `share -> ${r.status}`);
}

export function listChatGroups(): Promise<ChatGroup[]> {
  return json<ChatGroup[]>("/api/chat-groups");
}

export function createChatGroup(name: string): Promise<ChatGroup> {
  return json<ChatGroup>("/api/chat-groups", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ name }) });
}

export function renameChatGroup(id: number, name: string): Promise<ChatGroup> {
  return json<ChatGroup>(`/api/chat-groups/${id}`, { method: "PATCH", headers: jsonHeaders, body: JSON.stringify({ name }) });
}

export async function deleteChatGroup(id: number): Promise<void> {
  const r = await fetch(`/api/chat-groups/${id}`, { method: "DELETE", credentials: "include" });
  if (!r.ok) throw new ApiError(r.status, `DELETE /api/chat-groups/${id} -> ${r.status}`);
}

export function updateMe(body: { username?: string; email?: string; current_password?: string; new_password?: string }): Promise<Me> {
  return json<Me>("/api/me", { method: "PATCH", headers: jsonHeaders, body: JSON.stringify(body) });
}

export type AdminUser = { id: number; username: string; email: string; is_admin: boolean; is_active: boolean; group_id: number | null };
export type UsersFilters = { q?: string; status?: string; role?: string; group_id?: number };
export type UsersQuery = UsersFilters & { sort?: string; order?: string; page?: number; page_size?: number };
export type UsersPage = { items: AdminUser[]; total: number; page: number; page_size: number };
export type UsersStats = { total: number; active: number; inactive: number; admins: number };
export type BulkAction = "activate" | "deactivate" | "set_group" | "set_admin" | "delete";
export type BulkResult = { affected: number; skipped: { id: number; reason: string }[] };

function usersQs(query: Record<string, unknown> = {}): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  const qs = p.toString();
  return qs ? `?${qs}` : "";
}

export function adminListUsers(query: UsersQuery = {}): Promise<UsersPage> {
  return json<UsersPage>("/api/admin/users" + usersQs(query as Record<string, unknown>));
}

export function adminUsersStats(): Promise<UsersStats> {
  return json<UsersStats>("/api/admin/users/stats");
}

export function adminBulkUsers(body: { action: BulkAction; user_ids?: number[]; all_matching?: boolean; filters?: UsersFilters; group_id?: number | null; value?: boolean }): Promise<BulkResult> {
  return json<BulkResult>("/api/admin/users/bulk", { method: "POST", headers: jsonHeaders, body: JSON.stringify(body) });
}

export function adminUsersCsvUrl(filters: UsersFilters = {}): string {
  return "/api/admin/users/export.csv" + usersQs(filters as Record<string, unknown>);
}

export function adminCreateUser(body: { username: string; email: string; password: string; is_admin: boolean }): Promise<AdminUser> {
  return json<AdminUser>("/api/admin/users", { method: "POST", headers: jsonHeaders, body: JSON.stringify(body) });
}

export function adminUpdateUser(id: number, body: { is_active?: boolean; username?: string; email?: string; password?: string; is_admin?: boolean; group_id?: number | null }): Promise<AdminUser> {
  return json<AdminUser>(`/api/admin/users/${id}`, { method: "PATCH", headers: jsonHeaders, body: JSON.stringify(body) });
}

export async function adminDeleteUser(id: number): Promise<void> {
  const r = await fetch(`/api/admin/users/${id}`, { method: "DELETE", credentials: "include" });
  if (!r.ok) throw new ApiError(r.status, `DELETE /api/admin/users/${id} -> ${r.status}`);
}

export function adminListGroups(): Promise<{ id: number; name: string }[]> {
  return json<{ id: number; name: string }[]>("/api/admin/groups");
}

export function adminOverview(range?: string, userId?: number): Promise<AnalyticsOverview> {
  return json<AnalyticsOverview>("/api/admin/analytics/overview" + usersQs({ range, user_id: userId } as Record<string, unknown>));
}

export function adminPaths(range?: string, userId?: number): Promise<{ paths: AnalyticsPath[] }> {
  return json<{ paths: AnalyticsPath[] }>("/api/admin/analytics/paths" + usersQs({ range, user_id: userId } as Record<string, unknown>));
}

export function adminChats(query: { q?: string; user_id?: number; range?: string; sort?: string; order?: string; page?: number; page_size?: number } = {}): Promise<AnalyticsChatsPage> {
  return json<AnalyticsChatsPage>("/api/admin/analytics/chats" + usersQs(query as Record<string, unknown>));
}

export function adminModels(range?: string, userId?: number): Promise<ModelsResult> {
  return json<ModelsResult>("/api/admin/analytics/models" + usersQs({ range, user_id: userId } as Record<string, unknown>));
}

export function adminErrors(query: { range?: string; model?: string; user_id?: number; page?: number; page_size?: number } = {}): Promise<ErrorsResult> {
  return json<ErrorsResult>("/api/admin/analytics/errors" + usersQs(query as Record<string, unknown>));
}

export function adminAnalyticsOwners(): Promise<AnalyticsOwner[]> {
  return json<AnalyticsOwner[]>("/api/admin/analytics/owners");
}

export function adminChatsCsvUrl(filters: { q?: string; user_id?: number; range?: string; sort?: string; order?: string } = {}): string {
  return "/api/admin/analytics/chats/export.csv" + usersQs(filters as Record<string, unknown>);
}

export function adminChatDetail(id: number, range?: string): Promise<AnalyticsChatDetail> {
  return json<AnalyticsChatDetail>(`/api/admin/analytics/chats/${id}` + usersQs({ range }));
}

export async function emptyTrash(): Promise<void> {
  const r = await fetch("/api/chats/empty-trash", { method: "POST", credentials: "include" });
  if (!r.ok) throw new ApiError(r.status, `empty-trash -> ${r.status}`);
}
