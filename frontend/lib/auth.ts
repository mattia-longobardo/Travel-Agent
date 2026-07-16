export async function login(email: string, password: string): Promise<boolean> {
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  return r.ok;
}

export async function me(): Promise<{ username: string } | null> {
  const r = await fetch("/api/auth/me", { credentials: "include" });
  return r.ok ? r.json() : null;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
}
