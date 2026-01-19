"use client";

import React, { useEffect, useMemo, useState } from "react";
import { usePrefersReducedMotion } from "@/components/usePrefersReducedMotion";

export function ObsidianTerminal() {
  const lines = useMemo(
    () => [
      "[001] Protocol Initialized: A2A Settlement Layer",
      "[002] Discovery: Agent_Node_44 active on marketplace",
      "[003] Negotiating: Dynamic Pricing Model v2.1",
      "[004] Executing: Smart Escrow locked (Liquid Chrome Rail)",
      "[005] Verified: Output 0x77AF matches success criteria",
      "[006] Settled: +42.00 USDC transferred to Agent_Node_44",
      "[007] Human Interaction Required: FALSE",
    ],
    []
  );

  const [shown, setShown] = useState(0);
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    if (reduced) {
      setShown(lines.length);
      return;
    }

    const id = window.setInterval(() => {
      setShown((s) => (s < lines.length ? s + 1 : 0));
    }, 700);

    return () => window.clearInterval(id);
  }, [lines.length, reduced]);

  return (
    <div className="relative rounded-none border border-white/10 bg-white/5 backdrop-blur-xl">
      <div className="border-l-2 border-white/20 p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-xs uppercase tracking-[0.18em] text-white/60">Obsidian Terminal</div>
          <div className="text-[10px] tracking-[0.18em] text-white/40">LIVE</div>
        </div>

        <div className="font-mono text-sm leading-6 text-white/80">
          {lines.slice(0, shown).map((l) => {
            const isGlow = l.includes("Human Interaction Required: FALSE");
            return (
              <div
                key={l}
                className={isGlow ? "text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.55)]" : "text-white/75"}
              >
                {l}
              </div>
            );
          })}
          <div className="mt-2 text-white/30">{shown === 0 ? "…" : ""}</div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-0 shadow-[0_0_48px_rgba(255,255,255,0.06)]" />
    </div>
  );
}
