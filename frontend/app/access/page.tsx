"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { loginDev } from "@/services/auth";

export default function AccessPage() {
  const router = useRouter();
  const [tenantId, setTenantId] = useState("00000000-0000-0000-0000-000000000001");
  const [userId, setUserId] = useState("00000000-0000-0000-0000-000000000201");
  const [role, setRole] = useState("founder");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await loginDev({ tenant_id: tenantId, user_id: userId, role });
      router.push("/founder/security");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="platform-shell"><div className="platform-shell__inner"><form className="card" onSubmit={onSubmit} style={{ maxWidth: 640, margin: "2rem auto", display: "grid", gap: "1rem", padding: "1.5rem" }}><div className="label-caps" style={{ color: "var(--color-brand-orange)" }}>Developer access</div><h1>Generate local admin token</h1><p>This standalone repo uses explicit developer auth. It does not fabricate cross-tenant audit evidence.</p><label><div className="label-caps">Tenant ID</div><input value={tenantId} onChange={(e) => setTenantId(e.target.value)} style={{ width: "100%" }} /></label><label><div className="label-caps">User ID</div><input value={userId} onChange={(e) => setUserId(e.target.value)} style={{ width: "100%" }} /></label><label><div className="label-caps">Role</div><select value={role} onChange={(e) => setRole(e.target.value)}><option value="founder">founder</option><option value="agency_admin">agency_admin</option><option value="admin">admin</option><option value="viewer">viewer</option></select></label>{error ? <div style={{ color: "#fca5a5" }}>{error}</div> : null}<button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Create session"}</button></form></div></main>;
}