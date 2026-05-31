"use client";

import { useEffect, useRef, useState } from "react";
import { streamBuildUrl } from "@/lib/api";
import { detectAgent } from "@/lib/utils";
import type { AgentPhase } from "@/lib/utils";

export interface LogLine {
  id: string;
  text: string;
  agent?: AgentPhase;
}

export interface AgentState {
  name: string;
  status: "pending" | "running" | "success" | "failed";
  startedAt?: string;
  finishedAt?: string;
  lines: string[];
}

export type BuildState = "idle" | "running" | "success" | "failed";

const RECONNECT_BASE_MS = 1000;
const MAX_RECONNECTS = 20;

export function useStream(buildId: string | null) {
  const [logLines, setLogLines]   = useState<LogLine[]>([]);
  const [buildState, setBuildState] = useState<BuildState>("idle");
  const [agents, setAgents]       = useState<Record<string, AgentState>>({});

  const esRef             = useRef<EventSource | null>(null);
  const counterRef        = useRef(0);
  const reconnectCountRef = useRef(0);
  const timerRef          = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!buildId) {
      esRef.current?.close();
      setLogLines([]);
      setBuildState("idle");
      setAgents({});
      return;
    }

    reconnectCountRef.current = 0;

    function connect() {
      esRef.current?.close();
      const es = new EventSource(streamBuildUrl(buildId!));
      esRef.current = es;

      es.onopen = () => { reconnectCountRef.current = 0; };

      es.onmessage = (e) => {
        const raw: string = e.data;
        const id = `l${counterRef.current++}`;

        // Try structured JSON first
        try {
          const msg = JSON.parse(raw);
          if (msg.type === "build_complete" || msg.type === "done") {
            setBuildState(msg.status === "success" ? "success" : "failed");
            es.close();
            return;
          }
          if (msg.type === "agent_start") {
            setAgents((prev) => ({
              ...prev,
              [msg.agent]: {
                name: msg.agent,
                status: "running",
                startedAt: msg.started_at ?? new Date().toISOString(),
                lines: prev[msg.agent]?.lines ?? [],
              },
            }));
            setBuildState("running");
            return;
          }
          if (msg.type === "agent_done") {
            setAgents((prev) => ({
              ...prev,
              [msg.agent]: {
                ...prev[msg.agent],
                name: msg.agent,
                status: msg.status ?? "success",
                finishedAt: msg.finished_at ?? new Date().toISOString(),
                lines: prev[msg.agent]?.lines ?? [],
              },
            }));
            return;
          }
          if (msg.type === "log" && (msg.message || msg.text)) {
            const text = (msg.message ?? msg.text) as string;
            const agent = detectAgent(text) ?? msg.agent ?? undefined;
            const line: LogLine = { id, text, agent };
            setLogLines((prev) => [...prev, line]);
            if (agent) {
              setAgents((prev) => {
                const existing = prev[agent] ?? { name: agent, status: "running", startedAt: new Date().toISOString(), lines: [] };
                return { ...prev, [agent]: { ...existing, lines: [...existing.lines, id] } };
              });
              setBuildState("running");
            }
            return;
          }
        } catch { /* not JSON — treat as plain text */ }

        // Plain text log line
        const agent = detectAgent(raw) ?? undefined;
        const line: LogLine = { id, text: raw, agent };
        setLogLines((prev) => [...prev, line]);
        if (agent) {
          setAgents((prev) => {
            const existing = prev[agent] ?? { name: agent, status: "running", startedAt: new Date().toISOString(), lines: [] };
            // infer status from keywords
            const lower = raw.toLowerCase();
            let status = existing.status;
            if (lower.includes("starting") || lower.includes("→")) status = "running";
            if (lower.includes("succeeded") || lower.includes("success")) status = "success";
            if (lower.includes("failed") || lower.includes("error")) status = "failed";
            return { ...prev, [agent]: { ...existing, status, lines: [...existing.lines, id] } };
          });
          setBuildState("running");
        }
      };

      es.onerror = () => {
        es.close();
        if (reconnectCountRef.current >= MAX_RECONNECTS) return;
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(1.5, reconnectCountRef.current),
          15000
        );
        reconnectCountRef.current++;
        timerRef.current = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      esRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [buildId]);

  return { logLines, buildState, agents };
}
