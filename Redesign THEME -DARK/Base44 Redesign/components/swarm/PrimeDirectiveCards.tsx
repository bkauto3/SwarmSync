"use client";

import { motion } from "framer-motion";
import { Wallet, Network, TrendingUp } from "lucide-react";

const directives = [
  { icon: Wallet, title: "Initialize Logic & Liquidity", description: "Set guardrails and fund the autonomous wallet." },
  { icon: Network, title: "Autonomous Orchestration", description: "Agents recruit specialists from the Swarm marketplace." },
  { icon: TrendingUp, title: "Self-Correcting Growth", description: "Agents negotiate, pay, and verify each other." },
];

export default function PrimeDirectiveCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {directives.map((directive, index) => {
        const Icon = directive.icon;
        return (
          <motion.div
            key={directive.title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: index * 0.15 }}
            className="group relative"
          >
            <div
              className="h-full p-8 backdrop-blur-xl bg-white/5 border border-white/10 hover:border-white/20 transition-all duration-500"
              style={{ boxShadow: "inset 0 1px 0 0 rgba(255,255,255,0.05)" }}
            >
              <div className="absolute top-4 right-4 text-xs text-slate-600 font-mono">0{index + 1}</div>

              <div className="mb-6 relative">
                <div className="w-12 h-12 flex items-center justify-center bg-white/5 border border-white/10 group-hover:border-white/30 transition-colors">
                  <Icon className="w-5 h-5 text-slate-300 group-hover:text-white transition-colors" />
                </div>
              </div>

              <h3 className="text-white text-lg font-semibold tracking-tight mb-3">{directive.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{directive.description}</p>

              <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
