"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

type Entry = { id: string; text: string; glow: boolean };

const generateLogEntries = (): Entry[] => [
  { id: "001", text: "Protocol Initialized: A2A Settlement Layer", glow: false },
  { id: "002", text: "Discovery: Agent_Node_44 active on marketplace", glow: false },
  { id: "003", text: "Negotiating: Dynamic Pricing Model v2.1", glow: false },
  { id: "004", text: "Executing: Smart Escrow locked (Liquid Chrome Rail)", glow: false },
  { id: "005", text: "Verified: Output 0x77AF matches success criteria", glow: false },
  { id: "006", text: "Settled: +42.00 USDC transferred to Agent_Node_44", glow: false },
  { id: "007", text: "Human Interaction Required: FALSE", glow: true },
  { id: "008", text: "Scanning: Network topology updated", glow: false },
  { id: "009", text: "Active Agents: 127 nodes synchronized", glow: false },
  { id: "010", text: "Latency: 12ms cross-agent", glow: false },
  { id: "011", text: "Memory Pool: 94% optimized", glow: false },
  { id: "012", text: "Consensus: Block validated 0x9F2C", glow: false },
];

export default function ObsidianTerminal() {
  const [visibleEntries, setVisibleEntries] = useState<Entry[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [scanlinePosition, setScanlinePosition] = useState(0);

  const logEntries = generateLogEntries();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setVisibleEntries((prev) => {
        const next = [...prev, logEntries[currentIndex]];
        return next.slice(-20);
      });
      setCurrentIndex((prev) => (prev + 1) % logEntries.length);
    }, 400);

    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setScanlinePosition((prev) => (prev >= 100 ? 0 : prev + 1));
    }, 30);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <div className="hidden lg:block fixed right-0 top-0 h-screen w-[300px] bg-black/80 backdrop-blur-sm border-l border-white/10 overflow-hidden z-20">
      {/* Scanline */}
      <motion.div
        className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none"
        style={{ top: `${scanlinePosition}%` }}
      />

      {/* CRT overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-5"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, rgba(255,255,255,0.1) 0px, transparent 1px, transparent 2px, rgba(255,255,255,0.1) 3px)",
        }}
      />

      <div className="p-4 h-full overflow-hidden">
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-white/10">
          <div className="w-1 h-1 bg-green-400 animate-pulse" />
          <span className="text-[9px] text-slate-500 tracking-widest font-mono">LIVE DATA STREAM</span>
        </div>

        <div className="space-y-1 font-mono text-[10px] leading-tight">
          <AnimatePresence mode="sync">
            {visibleEntries.map((entry, index) => (
              <motion.div
                key={`${entry.id}-${index}`}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex gap-2 ${entry.glow ? "text-white" : "text-slate-500"}`}
                style={entry.glow ? { textShadow: "0 0 10px rgba(255,255,255,0.8)" } : {}}
              >
                <span className="text-slate-700 flex-shrink-0">{entry.id}</span>
                <span className="break-all">{entry.text}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
