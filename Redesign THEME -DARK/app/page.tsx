"use client";

import React from "react";
import { motion } from "framer-motion";
import { ChromeNetworkBackground } from "@/components/ChromeNetworkBackground";
import { GlossyButton } from "@/components/Buttons";
import { ObsidianTerminal } from "@/components/ObsidianTerminal";
import { VelocityGap } from "@/components/VelocityGap";
import { PrimeDirective } from "@/components/PrimeDirective";

export default function Page() {
  return (
    <main className="min-h-screen bg-black text-[#F8FAFC]">
      <ChromeNetworkBackground />

      <div className="relative z-10">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-black to-transparent" />

        <section className="mx-auto max-w-6xl px-5 pt-20 md:pt-28">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="grid grid-cols-1 gap-10 md:grid-cols-[1.1fr_0.9fr]"
          >
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-none border border-white/10 bg-white/5 px-3 py-2 backdrop-blur-xl">
                <span className="h-2 w-2 bg-white shadow-[0_0_14px_rgba(255,255,255,0.7)]" />
                <span className="text-xs tracking-[0.16em] uppercase text-white/70">
                  Obsidian & Liquid Chrome
                </span>
              </div>

              <h1
                className="text-4xl font-bold tracking-[-0.05em] md:text-6xl"
                style={{ textWrap: "balance" as any }}
              >
                The Zero-Touch Economy is Here.
              </h1>

              <p
                className="mt-4 max-w-xl text-base text-white/70 md:text-lg"
                style={{ textWrap: "balance" as any }}
              >
                When AI negotiates and pays AI, growth becomes instantaneous. Step out of the loop entirely.
              </p>

              <div className="mt-7 flex flex-wrap gap-3">
                <GlossyButton>Deploy Autonomous Workforce</GlossyButton>
                <GlossyButton variant="ghost">Visualize Live A2A Transactions</GlossyButton>
              </div>

              <div className="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-none border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Mode</div>
                  <div className="mt-1 text-sm tracking-tight text-white">Autonomous</div>
                </div>
                <div className="rounded-none border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Settlement</div>
                  <div className="mt-1 text-sm tracking-tight text-white">Atomic</div>
                </div>
                <div className="rounded-none border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Control</div>
                  <div className="mt-1 text-sm tracking-tight text-white">Guardrails</div>
                </div>
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.08 }}
              className="md:pt-2"
            >
              <ObsidianTerminal />
              <div className="mt-4 text-xs text-white/45">
                Signal trace reflects autonomous negotiation, escrow lock, verification, and settlement.
              </div>
            </motion.div>
          </motion.div>

          <div className="mt-14">
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5 }}
              className="mb-5 text-xs uppercase tracking-[0.18em] text-white/55"
            >
              The Velocity Gap
            </motion.div>
            <VelocityGap />
          </div>

          <div className="mt-14 pb-20">
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5 }}
              className="mb-5 text-xs uppercase tracking-[0.18em] text-white/55"
            >
              Prime Directive
            </motion.div>
            <PrimeDirective />
          </div>
        </section>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black to-transparent" />
      </div>
    </main>
  );
}
