"use client";

import { useCallback, useEffect, useState } from "react";
import type { Build } from "@/lib/api";
import { listBuilds } from "@/lib/api";

export function useBuildHistory(pollInterval = 5000) {
  const [builds, setBuilds] = useState<Build[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listBuilds();
      setBuilds(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load builds");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, pollInterval);
    return () => clearInterval(timer);
  }, [refresh, pollInterval]);

  return { builds, loading, error, refresh };
}
