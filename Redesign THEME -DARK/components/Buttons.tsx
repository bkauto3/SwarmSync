"use client";

import React from "react";

export function GlossyButton({
  children,
  variant = "primary",
}: {
  children: React.ReactNode;
  variant?: "primary" | "ghost";
}) {
  if (variant === "ghost") {
    return (
      <button className="group relative rounded-none border border-white/20 bg-white/0 px-5 py-3 text-sm font-semibold text-[#F8FAFC] tracking-tight transition hover:border-white/35 hover:bg-white/5">
        <span className="relative z-10">{children}</span>
        <span className="pointer-events-none absolute inset-0 opacity-0 transition group-hover:opacity-100">
          <span className="absolute inset-0 shadow-[0_0_24px_rgba(255,255,255,0.12)]" />
        </span>
      </button>
    );
  }

  return (
    <button className="group relative rounded-none bg-[#94A3B8] px-5 py-3 text-sm font-extrabold tracking-tight text-black transition hover:brightness-110">
      <span className="relative z-10">{children}</span>
      <span className="pointer-events-none absolute inset-0">
        <span className="absolute inset-x-0 top-0 h-1/2 bg-white/35 opacity-70" />
        <span className="absolute inset-0 shadow-[0_0_24px_rgba(255,255,255,0.18)] opacity-80 group-hover:opacity-100 transition" />
      </span>
    </button>
  );
}
