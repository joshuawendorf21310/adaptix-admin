import * as React from 'react';
import clsx from 'clsx';

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'critical' | 'info';

function toneStyles(tone: Tone) {
  switch (tone) {
    case 'accent': return { color: 'var(--color-brand-orange)', border: 'rgba(255,106,0,0.26)', background: 'rgba(255,106,0,0.10)' };
    case 'success': return { color: 'var(--color-status-active)', border: 'rgba(34,197,94,0.24)', background: 'rgba(34,197,94,0.10)' };
    case 'warning': return { color: 'var(--color-status-warning)', border: 'rgba(245,158,11,0.24)', background: 'rgba(245,158,11,0.10)' };
    case 'critical': return { color: 'var(--color-brand-red)', border: 'rgba(255,45,45,0.24)', background: 'rgba(255,45,45,0.10)' };
    case 'info': return { color: 'var(--color-status-info)', border: 'rgba(56,189,248,0.24)', background: 'rgba(56,189,248,0.10)' };
    default: return { color: 'var(--color-text-secondary)', border: 'var(--color-border-default)', background: 'rgba(255,255,255,0.03)' };
  }
}

export function StatusPill({ label, tone = 'neutral', className }: { label: string; tone?: Tone; className?: string }) {
  const styles = toneStyles(tone);
  return <span className={clsx('inline-flex items-center gap-2 border px-3 py-1.5 label-caps chamfer-8', className)} style={{ color: styles.color, borderColor: styles.border, background: styles.background }}><span className="h-1.5 w-1.5 rounded-full" style={{ background: styles.color }} />{label}</span>;
}

export function CommandPageHeader({ eyebrow, title, description, status }: { eyebrow: string; title: string; description: string; status?: React.ReactNode }) {
  return <section className="command-panel command-hero overflow-hidden p-6 md:p-8"><div className="space-y-3"><div className="label-caps text-[var(--color-brand-orange)]">{eyebrow}</div><div className="flex flex-wrap items-center gap-3"><h1 className="text-[clamp(1.75rem,3vw,2.75rem)] font-black uppercase tracking-[0.06em] text-text-primary">{title}</h1>{status}</div><p className="max-w-3xl text-sm leading-6 text-text-secondary md:text-[15px]">{description}</p></div></section>;
}

export function CommandPanel({ eyebrow, title, description, children }: { eyebrow?: string; title: string; description?: string; children: React.ReactNode }) {
  return <section className="command-panel p-5 md:p-6"><div className="mb-4 flex flex-col gap-3 border-b border-[var(--color-border-default)] pb-4"><div>{eyebrow ? <div className="label-caps text-text-muted">{eyebrow}</div> : null}<h2 className="mt-1 text-lg font-bold uppercase tracking-[0.08em] text-text-primary">{title}</h2>{description ? <p className="mt-2 text-sm text-text-secondary">{description}</p> : null}</div></div>{children}</section>;
}

export function MetricTile({ label, value, detail, tone = 'neutral' }: { label: string; value: string; detail?: string; tone?: Tone }) {
  const styles = toneStyles(tone);
  return <div className="command-panel p-4 md:p-5"><div className="label-caps text-text-muted">{label}</div><div className="mt-3 text-[clamp(1.5rem,2vw,2.15rem)] font-black tracking-[0.03em]" style={{ color: styles.color }}>{value}</div>{detail ? <div className="mt-2 text-xs text-text-secondary">{detail}</div> : null}</div>;
}

export function DataRow({ label, value, tone = 'neutral', detail }: { label: string; value: React.ReactNode; tone?: Tone; detail?: string }) {
  const styles = toneStyles(tone);
  return <div className="flex items-start justify-between gap-4 border-b border-[var(--color-border-subtle)] py-3 last:border-b-0"><div className="min-w-0"><div className="text-sm font-semibold text-text-primary">{label}</div>{detail ? <div className="mt-1 text-xs text-text-muted">{detail}</div> : null}</div><div className="shrink-0 text-right text-sm font-semibold" style={{ color: styles.color }}>{value}</div></div>;
}