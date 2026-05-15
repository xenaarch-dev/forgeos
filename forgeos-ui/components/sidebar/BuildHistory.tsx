"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, Clock, Search } from "lucide-react";
import { cn, formatDate, truncate } from "@/lib/utils";
import { staggerContainer, staggerItem } from "@/components/animations/variants";
import type { Build } from "@/lib/api";

function StatusIcon({ status }: { status: Build["status"] }) {
  if (status === "running") return <Loader2 className="h-3 w-3 text-status-running animate-spin" />;
  if (status === "success") return <CheckCircle2 className="h-3 w-3 text-status-success" />;
  if (status === "failed")  return <XCircle      className="h-3 w-3 text-status-error" />;
  return <Clock className="h-3 w-3 text-text-tertiary" />;
}

interface BuildHistoryProps {
  builds: Build[];
  activeBuildId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

export function BuildHistory({ builds, activeBuildId, onSelect, loading }: BuildHistoryProps) {
  const [query, setQuery] = useState("");

  const filtered = query.trim()
    ? builds.filter(
        (b) =>
          b.idea.toLowerCase().includes(query.toLowerCase()) ||
          b.id.includes(query)
      )
    : builds;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-4 w-4 animate-spin text-text-tertiary" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Search */}
      {builds.length > 0 && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-elevated px-3 py-1.5">
            <Search className="h-3 w-3 text-text-tertiary shrink-0" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search builds..."
              className="flex-1 bg-transparent text-xs text-text-primary placeholder:text-text-tertiary outline-none"
            />
          </div>
        </div>
      )}

      <p className="px-4 pb-1 text-[10px] font-semibold uppercase tracking-widest text-text-tertiary">
        Recent Builds
      </p>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center px-4">
            <Clock className="h-5 w-5 text-text-tertiary mb-2 opacity-40" />
            <p className="text-xs text-text-tertiary">
              {query ? "No matching builds" : "No builds yet"}
            </p>
          </div>
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="space-y-1"
          >
            <AnimatePresence>
              {filtered.map((build) => (
                <motion.button
                  key={build.id}
                  variants={staggerItem}
                  layout
                  onClick={() => onSelect(build.id)}
                  className={cn(
                    "w-full rounded-lg px-3 py-2.5 text-left transition-colors",
                    activeBuildId === build.id
                      ? "bg-accent/10 border border-accent/20"
                      : "border border-transparent hover:bg-bg-hover"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium text-text-primary leading-snug line-clamp-2">
                      {truncate(build.idea, 52)}
                    </p>
                    <StatusIcon status={build.status} />
                  </div>
                  <p className="mt-1 text-[10px] font-mono text-text-tertiary">
                    {formatDate(build.started_at)}
                  </p>
                </motion.button>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  );
}
