import Link from "next/link";

export default function HomePage() {
  return (
    <main className="platform-shell"><div className="platform-shell__inner card" style={{ padding: "1.5rem" }}><div className="label-caps" style={{ color: "var(--color-brand-orange)" }}>Adaptix Admin</div><h1>Standalone admin shell</h1><p>This repo hosts the extracted admin and governance experience. Authenticate with the local access page to exercise feature-flag and audit shell routes.</p><div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}><Link href="/access">Developer Access</Link><Link href="/founder/security">Security</Link></div></div></main>
  );
}