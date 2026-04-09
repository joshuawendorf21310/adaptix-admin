'use client';

import { useApi } from '@/hooks/useApi';
import {
  CommandPageHeader,
  CommandPanel,
  DataRow,
  MetricTile,
  StatusPill,
} from '@/components/command/CommandPrimitives';
import { AdaptixCardSkeleton } from '@/components/ui';

interface AuditIssues {
  empty_filters?: Array<{ file: string; line: number }>;
  missing_error_handling?: Array<{ file: string; line: number }>;
  hardcoded_values?: Array<{ file: string; line: number; value?: string }>;
  fake_implementations?: Array<{ file: string; line: number }>;
}
interface AuditReport {
  production_ready?: boolean;
  summary?: { total_issues: number; critical: number; warnings: number };
}

export default function PolicySandboxPage() {
  const issuesState = useApi<AuditIssues>('/api/v1/audit/issues');
  const auditState = useApi<AuditReport>('/api/v1/audit/production');

  const loading = issuesState.loading || auditState.loading;
  const issues = issuesState.data;
  const audit = auditState.data;

  const totalIssues = (issues?.empty_filters?.length ?? 0) +
    (issues?.missing_error_handling?.length ?? 0) +
    (issues?.hardcoded_values?.length ?? 0) +
    (issues?.fake_implementations?.length ?? 0);

  return (
    <div className="space-y-6 md:space-y-7">
      <CommandPageHeader
        eyebrow="Security"
        title="Policy Sandbox"
        description="Code-level policy audit — empty filters, hardcoded values, and error handling coverage."
        status={
          <StatusPill
            label={loading ? 'Loading…' : audit?.production_ready ? 'Production ready' : 'Issues found'}
            tone={loading ? 'neutral' : audit?.production_ready ? 'success' : 'warning'}
          />
        }
      />

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <AdaptixCardSkeleton key={i} />)}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricTile label="Total issues" value={String(totalIssues)} tone={totalIssues > 0 ? 'warning' : 'success'} />
            <MetricTile label="Fake impls" value={String(issues?.fake_implementations?.length ?? 0)} tone={(issues?.fake_implementations?.length ?? 0) > 0 ? 'critical' : 'success'} />
            <MetricTile label="Empty filters" value={String(issues?.empty_filters?.length ?? 0)} tone={(issues?.empty_filters?.length ?? 0) > 0 ? 'warning' : 'success'} />
            <MetricTile label="Hardcoded values" value={String(issues?.hardcoded_values?.length ?? 0)} tone={(issues?.hardcoded_values?.length ?? 0) > 0 ? 'warning' : 'success'} />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <CommandPanel eyebrow="Critical" title="Fake implementations" description="Code paths returning fake data that must be replaced before production.">
              {issues?.fake_implementations && issues.fake_implementations.length > 0 ? (
                issues.fake_implementations.map((item, i) => (
                  <DataRow
                    key={i}
                    label={item.file.split('/').slice(-2).join('/')}
                    value={`L${item.line}`}
                    tone="critical"
                  />
                ))
              ) : (
                <DataRow label="No fake implementations" value="Clean" tone="success" />
              )}
            </CommandPanel>

            <CommandPanel eyebrow="Security" title="Missing error handling" description="Functions with inadequate error handling coverage.">
              {issues?.missing_error_handling && issues.missing_error_handling.length > 0 ? (
                issues.missing_error_handling.slice(0, 8).map((item, i) => (
                  <DataRow
                    key={i}
                    label={item.file.split('/').slice(-2).join('/')}
                    value={`L${item.line}`}
                    tone="warning"
                  />
                ))
              ) : (
                <DataRow label="No missing error handling" value="Clean" tone="success" />
              )}
            </CommandPanel>
          </div>

          {issues?.hardcoded_values && issues.hardcoded_values.length > 0 && (
            <CommandPanel eyebrow="Configuration" title="Hardcoded values" description="Values that should be externalized to config or environment variables.">
              {issues.hardcoded_values.slice(0, 10).map((item, i) => (
                <DataRow
                  key={i}
                  label={item.file.split('/').slice(-2).join('/')}
                  value={`L${item.line}`}
                  tone="warning"
                  detail={item.value ? item.value.slice(0, 60) : undefined}
                />
              ))}
            </CommandPanel>
          )}
        </>
      )}
    </div>
  );
}
