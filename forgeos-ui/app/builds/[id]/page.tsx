"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useParams } from "next/navigation";
import { ArrowLeft, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import { getBuild, type Build } from "@/lib/api";
import { useStream } from "@/hooks/useStream";
import { AgentCard } from "@/components/build/AgentCard";
import { BuildLog } from "@/components/build/BuildLog";
import { StatusBadge } from "@/components/build/StatusBadge";
import { formatDuration, formatDate } from "@/lib/utils";

const AGENT_ORDER = ["architect", "scaffold", "coder", "security", "deploy"] as const;

export default function BuildPage() {
  const { id } = useParams<{ id: string }>();
  const [build, setBuild] = useState<Build | null>(null);
  const [notFound, setNotFound] = useState(false);

  const isRunning = build?.status === "running";
  const { logLines, buildState, agents } = useStream(isRunning ? id : null);

  useEffect(() => {
    if (!id) return;
    getBuild(id)
      .then(setBuild)
      .catch(() => setNotFound(true));
  }, [id]);

  if (notFound) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-8 w-8 text-status-error mb-3" />
          <p className="text-text-primary font-semibold">Build not found</p>
          <Link href="/" className="mt-4 inline-block text-sm text-accent hover:underline">
            ← Back to ForgeOS
          </Link>
        </div>
      </div>
    );
  }

  if (!build) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-accent" />
      </div>
    );
  }

  const status = isRunning ? buildState : build.status;

  return (
    <div className="min-h-screen px-6 py-8 max-w-5xl mx-auto relative z-10">
      {/* Back */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-text-tertiary hover:text-text-primary mb-8 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to ForgeOS
      </Link>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-text-primary leading-snug mb-1">
              {build.idea}
            </h1>
            <p className="font-mono text-xs text-text-tertiary">{build.id}</p>
          </div>
          <StatusBadge status={status === "idle" ? "pending" : status as any} />
        </div>

        {/* Meta */}
        <div className="flex items-center gap-4 mt-4 text-xs text-text-tertiary">
          <span className="flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            Started {formatDate(build.started_at)}
          </span>
          {build.finished_at && (
            <span className="flex items-center gap-1.5">
              {build.status === "success"
                ? <CheckCircle2 className="h-3 w-3 text-status-success" />
                : <XCircle className="h-3 w-3 text-status-error" />}
              {formatDuration(build.started_at, build.finished_at)}
            </span>
          )}
        </div>
      </motion.div>

      {/* Agent grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        {AGENT_ORDER.map((name) => {
          const agent = agents[name];
          if (!agent) return null;
          return <AgentCard key={name} agent={agent} allLines={logLines} />;
        })}
      </div>

      {/* Log */}
      <BuildLog lines={logLines} isRunning={isRunning} />
    </div>
  );
}
