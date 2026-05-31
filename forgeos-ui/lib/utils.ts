import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(startIso: string, endIso?: string | null): string {
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const secs = Math.round((end - start) / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return `${mins}m ${rem}s`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max - 1) + "…" : str;
}

export type LogClass = "normal" | "agent-start" | "agent-success" | "agent-error" | "agent-warn";

export function classifyLogLine(line: string): LogClass {
  const l = line.toLowerCase();
  if (l.includes("] starting") || l.includes("] start")) return "agent-start";
  if (l.includes("succeeded") || l.includes("success"))   return "agent-success";
  if (l.includes("failed") || l.includes("error") || l.includes("✖")) return "agent-error";
  if (l.includes("warning") || l.includes("warn"))        return "agent-warn";
  return "normal";
}

export type AgentPhase = "architect" | "scaffold" | "coder" | "security" | "deploy" | null;

export function detectAgent(line: string): AgentPhase {
  const l = line.toLowerCase();
  if (l.includes("[architect]") || l.includes("→ architect")) return "architect";
  if (l.includes("[scaffold]")  || l.includes("→ scaffold"))  return "scaffold";
  if (l.includes("[coder]")     || l.includes("→ coder"))     return "coder";
  if (l.includes("[security]")  || l.includes("→ security"))  return "security";
  if (l.includes("[deploy]")    || l.includes("→ deploy"))    return "deploy";
  return null;
}
