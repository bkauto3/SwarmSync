"use client";

import React from "react";
import { motion } from "framer-motion";
import { Network, Shield, Zap } from "lucide-react";

export function PrimeDirective() {
  const cards = [
    {
      icon: Shield,
      title: "Initialize Logic & Liquidity",
      body: "Set guardrails and fund the autonomous wallet.",
    },
    {
      icon: Network,
      title: "Autonomous Orchestration",
      body: "Agents recruit specialists from the Swarm marketplace.",
    },
    {
      icon: Zap,
      title: "Self-Correcting Growth",
      body: "Agents negotiate, pay, and verify each other.",
    },
  ] as const;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <motion.div
            key={c.title}
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            className="rounded-none border border-white/10 bg-white/5 p-6 backdrop-blur-xl"
          >
            <div className="mb-4 flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-none border border-white/15 bg-white/5">
                <Icon className="h-5 w-5 text-[#F8FAFC]" />
              </div>
              <div className="text-xs uppercase tracking-[0.18em] text-white/55">Prime Directive</div>
            </div>

            <div className="text-lg font-bold tracking-tight text-white">{c.title}</div>
            <div className="mt-2 text-sm text-white/65">{c.body}</div>
          </motion.div>
        );
      })}
    </div>
  );
}
