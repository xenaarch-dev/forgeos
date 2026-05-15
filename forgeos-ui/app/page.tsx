"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence, useScroll, useTransform } from "framer-motion";
import { CheckCircle2, XCircle, Zap, Terminal, Github, RefreshCw } from "lucide-react";

const HeroScene = dynamic(
  () => import("@/components/3d/HeroScene").then((m) => m.HeroScene),
  { ssr: false, loading: () => <div className="h-full w-full" /> }
);

import { Sidebar } from "@/components/sidebar/Sidebar";
import { IdeaInput } from "@/components/build/IdeaInput";
import { AgentCard } from "@/components/build/AgentCard";
import { BuildLog } from "@/components/build/BuildLog";
import { StatusBadge } from "@/components/build/StatusBadge";
import { useBuildHistory } from "@/hooks/useBuildHistory";
import { useStream } from "@/hooks/useStream";
import { startBuild } from "@/lib/api";
import { cn, formatDuration } from "@/lib/utils";

const AGENT_ORDER = ["architect", "scaffold", "coder", "security", "deploy"] as const;

const AGENT_COLORS: Record<string, string> = {
  architect: "#6366f1",
  scaffold:  "#34d399",
  coder:     "#a855f7",
  security:  "#f87171",
  deploy:    "#fbbf24",
};

export default function Home() {
  const [activeBuildId, setActiveBuildId] = useState<string | null>(null);
  const [currentIdea, setCurrentIdea]     = useState<string>("");
  const [submitting, setSubmitting]       = useState(false);
  const [error, setError]                 = useState<string | null>(null);
  const heroRef = useRef<HTMLDivElement>(null);

  const { builds, loading: historyLoading, refresh } = useBuildHistory(4000);
  const { logLines, buildState, agents } = useStream(activeBuildId);

  const { scrollY } = useScroll();
  const heroOpacity = useTransform(scrollY, [0, 300], [1, 0]);
  const heroScale   = useTransform(scrollY, [0, 300], [1, 0.92]);

  const handleSubmit = useCallback(async (idea: string) => {
    setSubmitting(true);
    setError(null);
    setCurrentIdea(idea);
    try {
      const { id } = await startBuild(idea);
      setActiveBuildId(id);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach ForgeOS API on :8000");
      setCurrentIdea("");
    } finally {
      setSubmitting(false);
    }
  }, [refresh]);

  const handleNewBuild = useCallback(() => {
    setActiveBuildId(null);
    setCurrentIdea("");
    setError(null);
  }, []);

  const handleSelectBuild = useCallback((id: string) => {
    setActiveBuildId(id);
    setCurrentIdea(builds.find((b) => b.id === id)?.idea ?? "");
  }, [builds]);

  const isBuilding = buildState === "running";
  const isIdle     = !activeBuildId;
  const elapsed    = activeBuildId
    ? formatDuration(builds.find((b) => b.id === activeBuildId)?.started_at ?? new Date().toISOString())
    : "";

  return (
    <div className="flex h-screen overflow-hidden relative z-10">
      <Sidebar
        builds={builds}
        activeBuildId={activeBuildId}
        onSelectBuild={handleSelectBuild}
        onNewBuild={handleNewBuild}
        loading={historyLoading}
      />

      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6 backdrop-blur-sm bg-bg/60">
          <div className="flex items-center gap-3">
            {activeBuildId && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-2.5"
              >
                <StatusBadge status={buildState === "idle" ? "pending" : buildState} />
                <span className="text-sm text-text-secondary font-mono tracking-tight">
                  {activeBuildId}
                </span>
                {elapsed && (
                  <span className="text-xs text-text-tertiary font-mono">{elapsed}</span>
                )}
              </motion.div>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-text-tertiary">
            <span className="font-mono font-semibold tracking-widest text-text-secondary">FORGEOS</span>
            <span className="opacity-30">·</span>
            <span className="font-mono">v0.2</span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            {isIdle ? (
              /* ── IDLE: full-screen hero ─────────────────────────── */
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={{ duration: 0.4 }}
                className="relative flex min-h-full flex-col items-center justify-center overflow-hidden"
              >
                {/* Full-screen 3D canvas */}
                <motion.div
                  ref={heroRef}
                  style={{ opacity: heroOpacity, scale: heroScale }}
                  className="absolute inset-0 pointer-events-none"
                >
                  <HeroScene className="h-full w-full" />
                </motion.div>

                {/* Content overlay */}
                <div className="relative z-10 flex flex-col items-center px-6 py-16">
                  {/* Logo mark */}
                  <motion.div
                    initial={{ opacity: 0, y: 20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ delay: 0.1, duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
                    className="mb-6 flex items-center gap-3"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent shadow-[0_0_24px_rgba(168,85,247,0.5)]">
                      <Zap className="h-5 w-5 text-white" />
                    </div>
                    <span className="text-3xl font-bold tracking-tight text-glow">ForgeOS</span>
                  </motion.div>

                  {/* Hero headline */}
                  <motion.h1
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.6 }}
                    className="mb-4 text-center text-6xl font-bold leading-[1.05] tracking-tight"
                  >
                    <span className="text-text-primary">One sentence.</span>
                    <br />
                    <span style={{ color: "#a855f7" }}>Full SaaS.</span>
                  </motion.h1>

                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3, duration: 0.6 }}
                    className="mb-10 text-center text-sm text-text-tertiary max-w-sm leading-relaxed font-mono"
                  >
                    architect → scaffold → code → secure → deploy
                  </motion.p>

                  {/* Agent pills */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.35, duration: 0.5 }}
                    className="mb-8 flex items-center gap-2 flex-wrap justify-center"
                  >
                    {AGENT_ORDER.map((name) => (
                      <span
                        key={name}
                        className="rounded-full border px-3 py-1 text-xs font-medium capitalize"
                        style={{
                          borderColor: AGENT_COLORS[name] + "40",
                          color: AGENT_COLORS[name],
                          backgroundColor: AGENT_COLORS[name] + "12",
                        }}
                      >
                        {name}
                      </span>
                    ))}
                  </motion.div>

                  {/* Error */}
                  <AnimatePresence>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="mb-6 flex items-start gap-2 rounded-lg border border-status-error/30 bg-status-error/8 px-4 py-3 text-sm text-status-error w-full max-w-2xl"
                      >
                        <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
                        <span>{error}</span>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <IdeaInput onSubmit={handleSubmit} isLoading={submitting} />
                </div>
              </motion.div>
            ) : (
              /* ── ACTIVE BUILD ─────────────────────────────────────── */
              <motion.div
                key={activeBuildId}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.35 }}
                className="px-6 py-6 space-y-5 max-w-5xl mx-auto"
              >
                {/* Build header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <h1 className="text-lg font-semibold text-text-primary leading-snug">
                      {currentIdea}
                    </h1>
                    <p className="mt-1 font-mono text-xs text-text-tertiary">
                      {activeBuildId}
                    </p>
                  </div>
                  <div className="shrink-0 flex items-center gap-3">
                    {buildState === "success" && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 text-status-success text-sm font-semibold"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        Build complete
                      </motion.div>
                    )}
                    {buildState === "failed" && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 text-status-error text-sm font-semibold"
                      >
                        <XCircle className="h-4 w-4" />
                        Build failed
                      </motion.div>
                    )}
                    <StatusBadge status={isBuilding ? "running" : buildState === "idle" ? "pending" : buildState} />
                  </div>
                </div>

                {/* Agent cards */}
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                  {AGENT_ORDER.map((name) => {
                    const agent = agents[name];
                    if (!agent) return null;
                    return (
                      <AgentCard
                        key={name}
                        agent={agent}
                        allLines={logLines}
                      />
                    );
                  })}
                </div>

                {/* Build log */}
                <BuildLog lines={logLines} isRunning={isBuilding} />

                {/* Post-build */}
                <AnimatePresence>
                  {(buildState === "success" || buildState === "failed") && (
                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="flex gap-3 pb-4"
                    >
                      <button
                        onClick={handleNewBuild}
                        className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold bg-accent text-white hover:bg-accent-hover transition-colors glow-purple"
                      >
                        <Zap className="h-4 w-4" />
                        New Build
                      </button>
                      {buildState === "failed" && (
                        <button
                          onClick={() => handleSubmit(currentIdea)}
                          className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium bg-bg-elevated text-text-secondary border border-border hover:bg-bg-hover transition-colors"
                        >
                          <RefreshCw className="h-4 w-4" />
                          Retry
                        </button>
                      )}
                      <a
                        href={`/builds/${activeBuildId}`}
                        className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium bg-bg-elevated text-text-secondary border border-border hover:bg-bg-hover transition-colors"
                      >
                        <Terminal className="h-4 w-4" />
                        View Details
                      </a>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
