"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, KeyRound, UserRound } from "lucide-react";
import { me, updateMe } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const router = useRouter();

  useEffect(() => { (async () => { const u = await me(); if (u) { setUsername(u.username); setEmail(u.email); } })(); }, []);

  async function saveProfile() {
    setErr(""); setMsg("");
    try { await updateMe({ username, email }); setMsg("Profilo aggiornato"); }
    catch { setErr("Errore: nome o email già in uso"); }
  }
  async function savePassword() {
    setErr(""); setMsg("");
    try { await updateMe({ current_password: cur, new_password: next }); setCur(""); setNext(""); setMsg("Password aggiornata"); }
    catch { setErr("Password attuale errata"); }
  }

  return (
    <main className="travel-map-pattern min-h-screen">
      <div className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-6 md:py-10">
        <div className="flex items-center gap-3">
          <Button type="button" variant="outline" size="icon" aria-label="Indietro" onClick={() => router.push("/")}>
            <ArrowLeft aria-hidden="true" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold">Impostazioni</h1>
            <p className="text-sm text-muted-foreground">Gestisci il tuo profilo e la tua password.</p>
          </div>
        </div>

        {(msg || err) && (
          <p role="status" className={`text-sm ${err ? "text-destructive" : "text-primary"}`}>{err || msg}</p>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><UserRound aria-hidden className="size-5" /> Profilo</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-3">
              <label className="flex flex-col gap-1.5 text-sm font-medium">Nome visualizzato
                <Input value={username} onChange={(e) => setUsername(e.target.value)} /></label>
              <label className="flex flex-col gap-1.5 text-sm font-medium">Email
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
              <Button onClick={saveProfile} className="self-start">Salva profilo</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><KeyRound aria-hidden className="size-5" /> Password</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-3">
              <label className="flex flex-col gap-1.5 text-sm font-medium">Password attuale
                <Input type="password" value={cur} onChange={(e) => setCur(e.target.value)} /></label>
              <label className="flex flex-col gap-1.5 text-sm font-medium">Nuova password
                <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} /></label>
              <Button onClick={savePassword} className="self-start">Cambia password</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
