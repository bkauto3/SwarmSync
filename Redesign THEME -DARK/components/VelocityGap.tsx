"use client";

import React from "react";

export function VelocityGap() {
  return (
    <div className="relative grid grid-cols-1 gap-6 rounded-none border border-white/10 bg-white/5 backdrop-blur-xl p-6 md:grid-cols-[1fr_auto_1fr] md:gap-10">
      <div>
        <div className="mb-3 text-xs uppercase tracking-[0.18em] text-white/50">Legacy Loop</div>
        <ul className="space-y-2 text-sm text-white/45">
          <li>Human Approval</li>
          <li>Negotiation Friction</li>
          <li>Net-30 Latency</li>
          <li>Linear Scaling</li>
        </ul>
      </div>

      <div className="relative hidden md:block">
        <div className="h-full w-px bg-white/10" />
        <div className="pointer-events-none absolute inset-0 shadow-[0_0_18px_rgba(255,255,255,0.35)]" />
      </div>

      <div>
        <div className="mb-3 text-xs uppercase tracking-[0.18em] text-white/60">Swarm Sync</div>
        <ul className="space-y-2 text-sm text-white">
          <li>Logic-Gate Execution</li>
          <li>Algorithmic Bidding</li>
          <li>Atomic Settlement</li>
          <li>Exponential Scaling</li>
        </ul>
      </div>
    </div>
  );
}
