"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PlatformShell } from "@/components/PlatformShell";

const LINKS = [
  { href: "/founder/security", label: "Security" },
  { href: "/founder/ai/policies", label: "AI Policies" },
];

export default function FounderLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const breadcrumbs = (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center" }}>
      <div>
        <div className="label-caps" style={{ color: "var(--color-brand-orange)" }}>Adaptix Admin</div>
        <h1 style={{ margin: "0.35rem 0" }}>Founder Controls</h1>
      </div>
      <nav style={{ display: "flex", gap: "0.75rem" }}>
        {LINKS.map((link) => <Link key={link.href} href={link.href} style={{ textDecoration: pathname.startsWith(link.href) ? "underline" : "none" }}>{link.label}</Link>)}
      </nav>
    </div>
  );
  return <PlatformShell breadcrumbs={breadcrumbs}>{children}</PlatformShell>;
}