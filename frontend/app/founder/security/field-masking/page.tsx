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

interface PersonnelMember {
  id: string;
  role: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  status?: string;
}
interface AuditReport {
  production_ready?: boolean;
  summary?: { total_issues: number; critical: number; warnings: number };
}

// PII fields that should be masked per role
const MASKED_FIELDS_BY_ROLE: Record<string, string[]> = {
  viewer: ['ssn', 'dob', 'insurance_id', 'phone', 'address'],
  dispatcher: ['ssn', 'insurance_id'],
  medic: ['ssn'],
  billing: ['ssn'],
  admin: [],
  agency_admin: [],
  founder: [],
};

export default function FieldMaskingPage() {
  const personnelState = useApi<PersonnelMember[]>('/api/v1/personnel/');
  const auditState = useApi<AuditReport>('/api/v1/audit/production');

  const loading = personnelState.loading || auditState.loading;
  const personnel = personnelState.data;
  const audit = auditState.data;

  const roleCounts = personnel
    ? personnel.reduce<Record<string, number>>((acc, p) => {
        acc[p.role] = (acc[p.role] ?? 0) + 1;
        return acc;
      }, {})
    : null;

  const highPrivilegeCount = personnel?.filter((p) =>
    ['founder', 'agency_admin', 'admin'].includes(p.role)
  ).length ?? 0;

  return (
    <div className="space-y-6 md:space-y-7">
      <CommandPageHeader
        eyebrow="Security"
        title="Field Masking"
        description="PII field visibility controls and role-based data masking configuration."
        status={
          <StatusPill
            label={loading ? 'Loading…' : audit?.production_ready ? 'Configured' : 'Review needed'}
            tone={loading ? 'neutral' : audit?.production_ready ? 'success' : 'warning'}
          />
        }
      />

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => <AdaptixCardSkeleton key={i} />)}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MetricTile label="Total users" value={String(personnel?.length ?? '—')} tone="info" />
            <MetricTile label="Privileged accounts" value={String(highPrivilegeCount)} tone={highPrivilegeCount > 5 ? 'warning' : 'success'} detail="admin, agency_admin, founder" />
            <MetricTile label="Unique roles" value={String(roleCounts ? Object.keys(roleCounts).length : '—')} tone="accent" />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <CommandPanel eyebrow="Role masking" title="PII masking by role" description="Fields masked per role in the field visibility policy.">
              {Object.entries(MASKED_FIELDS_BY_ROLE).map(([role, fields]) => (
                <DataRow
                  key={role}
                  label={role}
                  value={fields.length > 0 ? `${fields.length} fields masked` : 'Full access'}
                  tone={fields.length === 0 ? 'warning' : fields.length >= 3 ? 'success' : 'info'}
                  detail={fields.length > 0 ? fields.join(', ') : 'No PII restrictions'}
                />
              ))}
            </CommandPanel>

            <CommandPanel eyebrow="Access audit" title="Role distribution" description="Personnel count per role — used to size PII exposure risk.">
              {roleCounts && Object.keys(roleCounts).length > 0 ? (
                Object.entries(roleCounts)
                  .sort((a, b) => b[1] - a[1])
                  .map(([role, count]) => (
                    <DataRow
                      key={role}
                      label={role}
                      value={String(count)}
                      tone={['founder', 'agency_admin', 'admin'].includes(role) ? 'warning' : 'neutral'}
                      detail={`${MASKED_FIELDS_BY_ROLE[role]?.length ?? 0} masked fields`}
                    />
                  ))
              ) : (
                <DataRow label="No personnel data" value="—" tone="neutral" />
              )}
            </CommandPanel>
          </div>
        </>
      )}
    </div>
  );
}
