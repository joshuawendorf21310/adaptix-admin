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
  first_name?: string;
  last_name?: string;
  role: string;
  status?: string;
  email?: string;
}

const ROLE_DESCRIPTIONS: Record<string, string> = {
  founder: 'Full platform access and billing command',
  agency_admin: 'Full agency access including billing and configuration',
  admin: 'Administrative access including user management',
  medic: 'Field operations: ePCR, dispatch, scheduling',
  billing: 'Billing and AR access only',
  dispatcher: 'CAD and dispatch access',
  viewer: 'Read-only access to assigned modules',
};

const ROLE_TONE: Record<string, 'critical' | 'warning' | 'accent' | 'success' | 'info' | 'neutral'> = {
  founder: 'critical',
  agency_admin: 'warning',
  admin: 'accent',
  medic: 'success',
  billing: 'info',
  dispatcher: 'info',
  viewer: 'neutral',
};

export default function RoleBuilderPage() {
  const { data: personnel, loading, error } = useApi<PersonnelMember[]>('/personnel/');

  const roleCounts = personnel
    ? personnel.reduce<Record<string, number>>((acc, p) => {
        acc[p.role] = (acc[p.role] ?? 0) + 1;
        return acc;
      }, {})
    : null;

  const activeCount = personnel?.filter((p) => p.status === 'active').length ?? 0;
  const uniqueRoles = roleCounts ? Object.keys(roleCounts).length : 0;

  return (
    <div className="space-y-6 md:space-y-7">
      <CommandPageHeader
        eyebrow="Security"
        title="Role Builder"
        description="Personnel role assignments and RBAC posture across the platform."
        status={
          <StatusPill
            label={loading ? 'Loading…' : error ? 'Error' : 'Live'}
            tone={loading ? 'neutral' : error ? 'critical' : 'info'}
          />
        }
      />

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <AdaptixCardSkeleton key={i} />)}
        </div>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading personnel data: {error}</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MetricTile
              label="Total personnel"
              value={String(personnel?.length ?? 0)}
              tone="info"
            />
            <MetricTile
              label="Active"
              value={String(activeCount)}
              tone="success"
            />
            <MetricTile
              label="Unique roles"
              value={String(uniqueRoles)}
              tone="accent"
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <CommandPanel eyebrow="RBAC" title="Role distribution" description="Personnel count per assigned role.">
              {roleCounts && Object.keys(roleCounts).length > 0 ? (
                Object.entries(roleCounts)
                  .sort((a, b) => b[1] - a[1])
                  .map(([role, count]) => (
                    <DataRow
                      key={role}
                      label={role}
                      value={String(count)}
                      tone={ROLE_TONE[role] ?? 'neutral'}
                      detail={ROLE_DESCRIPTIONS[role] ?? 'Custom role'}
                    />
                  ))
              ) : (
                <DataRow label="No personnel found" value="—" tone="neutral" />
              )}
            </CommandPanel>

            <CommandPanel eyebrow="Personnel" title="Privileged accounts" description="Accounts with administrative or founder-level access.">
              {personnel
                ?.filter((p) => ['founder', 'agency_admin', 'admin'].includes(p.role))
                .slice(0, 10)
                .map((p) => (
                  <DataRow
                    key={p.id}
                    label={[p.first_name, p.last_name].filter(Boolean).join(' ') || p.email || p.id}
                    value={p.role}
                    tone={ROLE_TONE[p.role] ?? 'neutral'}
                    detail={p.status ?? 'unknown status'}
                  />
                )) ?? (
                <DataRow label="No privileged accounts" value="—" tone="neutral" />
              )}
            </CommandPanel>
          </div>

          <CommandPanel eyebrow="Role reference" title="Defined roles" description="Platform role definitions and access scopes.">
            {Object.entries(ROLE_DESCRIPTIONS).map(([role, desc]) => (
              <DataRow key={role} label={role} value="Active" tone={ROLE_TONE[role] ?? 'neutral'} detail={desc} />
            ))}
          </CommandPanel>
        </>
      )}
    </div>
  );
}
