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

interface AuditReport {
  production_ready: boolean;
  summary: { total_issues: number; critical: number; warnings: number };
  details?: {
    empty_filters?: Array<{ file: string; line: number; code: string }>;
    missing_error_handling?: Array<{ file: string; line: number }>;
    hardcoded_values?: Array<{ file: string; line: number; value: string }>;
    fake_implementations?: Array<{ file: string; line: number }>;
  };
}
interface TodoItem {
  file: string;
  line: number;
  text: string;
  type: string;
}

export default function AccessLogsPage() {
  const auditState = useApi<AuditReport>('/api/v1/audit/production');
  const todosState = useApi<TodoItem[]>('/api/v1/audit/todos');

  const loading = auditState.loading || todosState.loading;
  const audit = auditState.data;
  const todos = todosState.data;

  return (
    <div className="space-y-6 md:space-y-7">
      <CommandPageHeader
        eyebrow="Security"
        title="Access Logs & Audit"
        description="Production audit scan, code quality findings, and outstanding TODOs."
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
            <MetricTile
              label="Total issues"
              value={String(audit?.summary.total_issues ?? '—')}
              tone={audit && audit.summary.total_issues > 0 ? 'warning' : 'success'}
            />
            <MetricTile
              label="Critical"
              value={String(audit?.summary.critical ?? '—')}
              tone={audit && audit.summary.critical > 0 ? 'critical' : 'success'}
            />
            <MetricTile
              label="Warnings"
              value={String(audit?.summary.warnings ?? '—')}
              tone={audit && audit.summary.warnings > 0 ? 'warning' : 'success'}
            />
            <MetricTile
              label="Open TODOs"
              value={String(todos?.length ?? '—')}
              tone={todos && todos.length > 10 ? 'warning' : 'neutral'}
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <CommandPanel eyebrow="Code quality" title="Audit findings" description="Scan results across key code quality categories.">
              <DataRow
                label="Empty filters"
                value={String(audit?.details?.empty_filters?.length ?? 0)}
                tone={audit?.details?.empty_filters?.length ? 'warning' : 'success'}
              />
              <DataRow
                label="Missing error handling"
                value={String(audit?.details?.missing_error_handling?.length ?? 0)}
                tone={audit?.details?.missing_error_handling?.length ? 'warning' : 'success'}
              />
              <DataRow
                label="Hardcoded values"
                value={String(audit?.details?.hardcoded_values?.length ?? 0)}
                tone={audit?.details?.hardcoded_values?.length ? 'warning' : 'success'}
              />
              <DataRow
                label="Fake implementations"
                value={String(audit?.details?.fake_implementations?.length ?? 0)}
                tone={audit?.details?.fake_implementations?.length ? 'critical' : 'success'}
              />
            </CommandPanel>

            <CommandPanel eyebrow="Backlog" title="Open TODOs" description="Outstanding TODO/FIXME comments in the codebase.">
              {todos && todos.length > 0 ? (
                todos.slice(0, 10).map((todo, idx) => (
                  <DataRow
                    key={idx}
                    label={todo.file.split('/').slice(-2).join('/')}
                    value={todo.type}
                    tone="warning"
                    detail={todo.text.length > 80 ? todo.text.slice(0, 80) + '…' : todo.text}
                  />
                ))
              ) : (
                <DataRow label="No open TODOs" value="Clean" tone="success" />
              )}
            </CommandPanel>
          </div>

          {audit?.details?.fake_implementations && audit.details.fake_implementations.length > 0 && (
            <CommandPanel eyebrow="Critical" title="Fake implementations detected" description="These must be replaced before production deployment.">
              {audit.details.fake_implementations.map((item, idx) => (
                <DataRow
                  key={idx}
                  label={item.file.split('/').slice(-2).join('/')}
                  value={`L${item.line}`}
                  tone="critical"
                />
              ))}
            </CommandPanel>
          )}
        </>
      )}
    </div>
  );
}
