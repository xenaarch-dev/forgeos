"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PanelLeftClose, PanelLeftOpen, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { BuildHistory } from "./BuildHistory";
import type { Build } from "@/lib/api";

interface SidebarProps {
  builds: Build[];
  activeBuildId: string | null;
  onSelectBuild: (id: string) => void;
  onNewBuild: () => void;
  loading: boolean;
}

export function Sidebar({ builds, activeBuildId, onSelectBuild, onNewBuild, loading }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside
      animate={{ width: collapsed ? 56 : 272 }}
      transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
      className="relative flex h-full shrink-0 flex-col border-r border-border bg-bg-surface overflow-hidden"
      style={{ zIndex: 20 }}
    >
      {/* Header */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-2"
            >
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent shadow-[0_0_10px_rgba(168,85,247,0.4)]">
                <Zap className="h-3.5 w-3.5 text-white" />
              </div>
              <span className="text-sm font-bold text-text-primary tracking-tight">ForgeOS</span>
            </motion.div>
          )}
        </AnimatePresence>

        <button
          onClick={() => setCollapsed((p) => !p)}
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            "text-text-tertiary hover:bg-bg-hover hover:text-text-primary transition-colors",
            collapsed && "mx-auto"
          )}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {/* New Build button */}
      <div className="shrink-0 p-3">
        <motion.button
          onClick={onNewBuild}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          className={cn(
            "flex items-center gap-2 rounded-xl transition-all w-full",
            "bg-accent/10 text-accent hover:bg-accent/20 border border-accent/20",
            "hover:shadow-[0_0_12px_rgba(168,85,247,0.15)]",
            collapsed ? "justify-center p-2.5" : "px-3 py-2.5"
          )}
        >
          <Zap className="h-4 w-4 shrink-0" />
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="text-sm font-semibold whitespace-nowrap overflow-hidden"
              >
                New Build
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Build history */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex-1 overflow-hidden"
          >
            <BuildHistory
              builds={builds}
              activeBuildId={activeBuildId}
              onSelect={onSelectBuild}
              loading={loading}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}
