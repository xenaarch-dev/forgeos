const BASE = "/api";

export type BuildStatus = "running" | "success" | "failed" | "pending";

export interface Build {
  id: string;
  idea: string;
  status: BuildStatus;
  started_at: string;
  finished_at: string | null;
  workdir: string;
}

export interface StartBuildResponse {
  id: string;
  status: BuildStatus;
}

export async function startBuild(idea: string): Promise<StartBuildResponse> {
  const res = await fetch(`${BASE}/builds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to start build: ${res.status} ${text}`);
  }
  return res.json();
}

export async function listBuilds(): Promise<Build[]> {
  const res = await fetch(`${BASE}/builds`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to list builds: ${res.status}`);
  return res.json();
}

export async function getBuild(id: string): Promise<Build> {
  const res = await fetch(`${BASE}/builds/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Build not found: ${id}`);
  return res.json();
}

export function streamBuildUrl(id: string): string {
  return `${BASE}/builds/${id}/stream`;
}
