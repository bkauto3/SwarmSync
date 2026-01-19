"use client";

import { motion } from "framer-motion";
import { XCircle, Zap } from "lucide-react";

const legacyItems = ["Human Approval", "Negotiation Friction", "Net-30 Latency", "Linear Scaling"];
const swarmItems = ["Logic-Gate Execution", "Algorithmic Bidding", "Atomic Settlement", "Exponential Scaling"];

export default function VelocityGapComparison() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
      className="relative"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
        <div className="p-8 md:p-12 md:pr-16">
          <h3 className="text-slate-500 text-xs tracking-widest uppercase mb-8 font-medium">Legacy Loop</h3>
          <ul className="space-y-5">
            {legacyItems.map((item, index) => (
              <motion.li
                key={item}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="flex items-center gap-4 text-slate-500"
              >
                <XCircle className="w-4 h-4 text-slate-600 flex-shrink-0" />
                <span className="text-lg">{item}</span>
              </motion.li>
            ))}
          </ul>
        </div>

        <div className="hidden md:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-3/4">
          <div
            className="w-px h-full bg-white/30"
            style={{
              boxShadow:
                "0 0 20px rgba(255,255,255,0.5), 0 0 40px rgba(255,255,255,0.3), 0 0 60px rgba(255,255,255,0.1)",
            }}
          />
        </div>

        <div className="md:hidden w-full px-8">
          <div
            className="h-px w-full bg-white/30"
            style={{ boxShadow: "0 0 20px rgba(255,255,255,0.5), 0 0 40px rgba(255,255,255,0.3)" }}
          />
        </div>

        <div className="p-8 md:p-12 md:pl-16">
          <h3 className="text-white text-xs tracking-widest uppercase mb-8 font-medium">Swarm Sync</h3>
          <ul className="space-y-5">
            {swarmItems.map((item, index) => (
              <motion.li
                key={item}
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="flex items-center gap-4 text-white"
              >
                <Zap className="w-4 h-4 text-white flex-shrink-0" />
                <span className="text-lg font-medium">{item}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
    </motion.div>
  );
}
