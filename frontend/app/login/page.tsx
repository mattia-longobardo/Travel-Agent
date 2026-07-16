"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";
import { login } from "@/lib/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { BrandLockup } from "@/components/Brand";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [p, setP] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [err, setErr] = useState("");
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (await login(email, p)) router.push("/");
    else setErr("Credenziali non valide");
  }

  return (
    <main className="travel-map-pattern grid min-h-screen place-items-center bg-background px-4 py-8">
      <Card className="w-full max-w-md rounded-lg border bg-card/95 shadow-xl">
        <CardHeader className="items-center gap-4 text-center">
          <BrandLockup />
          <p className="text-sm text-muted-foreground">Dove vuoi andare? Al resto pensiamo noi.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              Email
              <span className="relative">
                <Mail aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} className="pl-9" />
              </span>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              Password
              <span className="relative">
                <LockKeyhole aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="password"
                  value={p}
                  onChange={(e) => setP(e.target.value)}
                  className="px-9"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Nascondi password" : "Mostra password"}
                  aria-pressed={showPassword}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none"
                >
                  {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
                </button>
              </span>
            </label>
            {err && <p className="text-sm text-destructive">{err}</p>}
            <Button type="submit" className="mt-2 w-full">
              Accedi
              <ArrowRight data-icon="inline-end" aria-hidden="true" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
