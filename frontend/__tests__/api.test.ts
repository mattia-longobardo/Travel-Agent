import { listChats, createChat, getMessages, listChatGroups, setChatStatus, shareChat, adminListUsers, adminUsersCsvUrl, adminChats, adminChatsCsvUrl, adminModels } from "@/lib/api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

test("listChats GETs /api/chats and returns array", async () => {
  const f = mockFetch(200, [{ id: 1, title: "A", params_json: {}, owner_id: 1, permission: "owner" }]);
  vi.stubGlobal("fetch", f);
  const res = await listChats();
  expect(f).toHaveBeenCalledWith("/api/chats", expect.objectContaining({ credentials: "include" }));
  expect(res[0].id).toBe(1);
});

test("createChat POSTs title to /api/chats", async () => {
  const f = mockFetch(201, { id: 5, title: "Nuova chat", params_json: {}, owner_id: 1, permission: "owner" });
  vi.stubGlobal("fetch", f);
  const res = await createChat("Nuova chat");
  const [url, opts] = f.mock.calls[0];
  expect(url).toBe("/api/chats");
  expect(opts.method).toBe("POST");
  expect(JSON.parse(opts.body)).toEqual({ title: "Nuova chat" });
  expect(res.id).toBe(5);
});

test("getMessages GETs the messages collection", async () => {
  const f = mockFetch(200, []);
  vi.stubGlobal("fetch", f);
  await getMessages(7);
  expect(f).toHaveBeenCalledWith("/api/chats/7/messages", expect.objectContaining({ credentials: "include" }));
});

test("listChatGroups GETs /api/chat-groups", async () => {
  const f = mockFetch(200, []);
  vi.stubGlobal("fetch", f);
  await listChatGroups();
  expect(f).toHaveBeenCalledWith("/api/chat-groups", expect.objectContaining({ credentials: "include" }));
});

test("setChatStatus PATCHes status", async () => {
  const f = mockFetch(200, {});
  vi.stubGlobal("fetch", f);
  await setChatStatus(3, "archived");
  const [url, opts] = f.mock.calls[0];
  expect(url).toBe("/api/chats/3"); expect(opts.method).toBe("PATCH");
  expect(JSON.parse(opts.body)).toEqual({ status: "archived" });
});

test("shareChat POSTs email + permission", async () => {
  const f = mockFetch(200, {});
  vi.stubGlobal("fetch", f);
  await shareChat(3, "x@y.it", "write");
  const [url, opts] = f.mock.calls[0];
  expect(url).toBe("/api/chats/3/share");
  expect(JSON.parse(opts.body)).toEqual({ email: "x@y.it", permission: "write" });
});

test("listChats with status adds query", async () => {
  const f = mockFetch(200, []);
  vi.stubGlobal("fetch", f);
  await listChats("trashed");
  expect(f).toHaveBeenCalledWith("/api/chats?status=trashed", expect.objectContaining({ credentials: "include" }));
});

test("emptyTrash POSTs to /api/chats/empty-trash", async () => {
  const f = mockFetch(200, { status: "ok", deleted: 2 });
  vi.stubGlobal("fetch", f);
  await (await import("@/lib/api")).emptyTrash();
  const [url, opts] = f.mock.calls[0];
  expect(url).toBe("/api/chats/empty-trash"); expect(opts.method).toBe("POST");
});

test("adminOverview GETs the overview endpoint", async () => {
  const f = mockFetch(200, { total_chats: 1 });
  vi.stubGlobal("fetch", f);
  const { adminOverview } = await import("@/lib/api");
  await adminOverview();
  expect(f).toHaveBeenCalledWith("/api/admin/analytics/overview", expect.objectContaining({ credentials: "include" }));
});

test("adminPaths GETs the paths endpoint", async () => {
  const f = mockFetch(200, { paths: [] });
  vi.stubGlobal("fetch", f);
  const { adminPaths } = await import("@/lib/api");
  await adminPaths();
  expect(f).toHaveBeenCalledWith("/api/admin/analytics/paths", expect.objectContaining({ credentials: "include" }));
});

test("adminChats builds the sort/order query string", async () => {
  const f = mockFetch(200, []);
  vi.stubGlobal("fetch", f);
  const { adminChats } = await import("@/lib/api");
  await adminChats({ sort: "last_message_at", order: "desc" });
  const [url] = f.mock.calls[0];
  expect(url).toBe("/api/admin/analytics/chats?sort=last_message_at&order=desc");
});

test("adminChats adds the user_id filter", async () => {
  const f = mockFetch(200, []);
  vi.stubGlobal("fetch", f);
  const { adminChats } = await import("@/lib/api");
  await adminChats({ user_id: 7 });
  const [url] = f.mock.calls[0];
  expect(url).toBe("/api/admin/analytics/chats?user_id=7");
});

test("adminChats with no args hits the bare endpoint", async () => {
  const f = mockFetch(200, []);
  vi.stubGlobal("fetch", f);
  const { adminChats } = await import("@/lib/api");
  await adminChats();
  const [url] = f.mock.calls[0];
  expect(url).toBe("/api/admin/analytics/chats");
});

test("adminChatDetail propagates the analytics range", async () => {
  const f = mockFetch(200, {});
  vi.stubGlobal("fetch", f);
  const { adminChatDetail } = await import("@/lib/api");
  await adminChatDetail(42, "7d");
  expect(f).toHaveBeenCalledWith("/api/admin/analytics/chats/42?range=7d", expect.objectContaining({ credentials: "include" }));
});

test("adminListUsers builds query string and returns envelope", async () => {
  const f = mockFetch(200, { items: [], total: 0, page: 2, page_size: 25 });
  vi.stubGlobal("fetch", f);
  const r = await adminListUsers({ q: "bo b", status: "active", page: 2, page_size: 25 });
  const url = (f.mock.calls[0][0] as string);
  expect(url).toContain("/api/admin/users?");
  expect(url).toContain("q=bo+b");
  expect(url).toContain("status=active");
  expect(r.page).toBe(2);
});

test("adminUsersCsvUrl encodes filters", () => {
  expect(adminUsersCsvUrl({ q: "x", role: "admin" }))
    .toBe("/api/admin/users/export.csv?q=x&role=admin");
});

test("adminCreateUser POSTs new user", async () => {
  const f = mockFetch(201, { id: 9, username: "carl", email: "c@x", is_admin: false, is_active: true });
  vi.stubGlobal("fetch", f);
  const { adminCreateUser } = await import("@/lib/api");
  await adminCreateUser({ username: "carl", email: "c@x", password: "pw", is_admin: false });
  const [url, opts] = f.mock.calls[0];
  expect(url).toBe("/api/admin/users"); expect(opts.method).toBe("POST");
  expect(JSON.parse(opts.body)).toEqual({ username: "carl", email: "c@x", password: "pw", is_admin: false });
});

test("adminChats sends query and returns envelope", async () => {
  const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }), { status: 200 }) as Response);
  const r = await adminChats({ q: "rom", range: "7d", page: 1, sort: "total_tokens", order: "desc" });
  const url = spy.mock.calls[0][0] as string;
  expect(url).toContain("/api/admin/analytics/chats?");
  expect(url).toContain("q=rom");
  expect(url).toContain("range=7d");
  expect(r.total).toBe(0);
  spy.mockRestore();
});

test("adminChatsCsvUrl + adminModels build URLs", async () => {
  expect(adminChatsCsvUrl({ q: "x", range: "30d" }))
    .toBe("/api/admin/analytics/chats/export.csv?q=x&range=30d");
  const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [], total_cost_usd: 0, has_unpriced: false }), { status: 200 }) as Response);
  await adminModels("90d");
  expect(spy.mock.calls[0][0]).toContain("/api/admin/analytics/models?range=90d");
  spy.mockRestore();
});
