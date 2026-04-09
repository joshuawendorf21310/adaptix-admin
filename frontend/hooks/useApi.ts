"use client";

import { useCallback, useEffect, useState } from "react";

import { getStoredAuthToken } from "@/services/auth";

const API_BASE = process.env.NEXT_PUBLIC_ADMIN_API_BASE ?? "http://127.0.0.1:8012";

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!path) { setLoading(false); setData(null); setError(null); return; }
    setLoading(true); setError(null);
    try {
      const token = getStoredAuthToken();
      const response = await fetch(`${API_BASE}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined, cache: "no-store" });
      if (!response.ok) throw new Error(await response.text() || `Request failed with ${response.status}`);
      setData(await response.json() as T);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => { void refetch(); }, [refetch]);
  return { data, loading, error, refetch };
}