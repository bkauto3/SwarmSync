"use client";

import { motion } from "framer-motion";
import ChromeNetworkBackground from "@/components/swarm/ChromeNetworkBackground";
import ObsidianTerminal from "@/components/swarm/ObsidianTerminal";
import VelocityGapComparison from "@/components/swarm/VelocityGapComparison";
import PrimeDirectiveCards from "@/components/swarm/PrimeDirectiveCards";
import TacticalButton from "@/components/swarm/TacticalButton";
import GlitchHeadline from "@/components/swarm/GlitchHeadline";
import DepthFieldOrbs from "@/components/swarm/DepthFieldOrbs";

export default function SwarmSyncLanding() {
  return (
    <div className="min-h-screen bg-black text-slate-50 overflow-x-hidden">
      <ChromeNetworkBackground />
      <ObsidianTerminal />

      {/* Logo with Halo Effect */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1, delay: 0.2 }}
        className="fixed top-8 left-1/2 -translate-x-1/2 z-30"
      >
        <div className="relative">
          <div
            className="absolute inset-0 -m-20"
            style={{
              background: "radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%)",
              filter: "blur(40px)",
              transform: "scale(1.5)",
            }}
          />
          <img
            src="https://qtrypzzcjebvfcihiynt.supabase.co/storage/v1/object/public/base44-prod/public/694e9b327815227aec41aef7/c8322e436_SwarmSyncNEWnoBack.png"
            alt="Swarm Sync"
            className="relative w-32 h-auto"
            style={{ mixBlendMode: "normal" }}
          />
        </div>
      </motion.div>

      {/* Hero Section */}
      <section className="relative z-10 px-6 md:px-12 pt-56 md:pt-64 pb-24 lg:mr-[300px]">
        <DepthFieldOrbs />
        <div className="max-w-5xl mx-auto">
          <GlitchHeadline className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tighter leading-[1.1] mb-8">
            The Zero-Touch
            <br />
            Economy is Here.
          </GlitchHeadline>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="text-lg md:text-xl text-slate-400 max-w-2xl mb-12 leading-relaxed font-mono"
          >
            When AI negotiates and pays AI, growth becomes instantaneous. Step out of the loop entirely.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.9 }}
            className="flex flex-col sm:flex-row gap-4"
          >
            <TacticalButton>Deploy Workforce</TacticalButton>
            <TacticalButton variant="ghost">Live A2A Feed</TacticalButton>
          </motion.div>
        </div>
      </section>

      {/* Velocity Gap */}
      <section id="velocity" className="relative z-10 px-6 md:px-12 py-24 lg:mr-[300px]">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <p className="text-xs tracking-widest text-slate-500 uppercase mb-4">The Velocity Gap</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tighter">Why Autonomy Wins</h2>
          </motion.div>

          <VelocityGapComparison />
        </div>
      </section>

      {/* Prime Directive */}
      <section id="prime" className="relative z-10 px-6 md:px-12 py-24 pb-32 lg:mr-[300px]">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <p className="text-xs tracking-widest text-slate-500 uppercase mb-4">The Prime Directive</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tighter mb-4">How It Works</h2>
            <p className="text-slate-400 max-w-xl mx-auto">Three steps to autonomous economic participation.</p>
          </motion.div>

          <PrimeDirectiveCards />
        </div>
      </section>

      {/* Footer CTA */}
      <section className="relative z-10 px-6 md:px-12 py-24 border-t border-white/10 lg:mr-[300px]">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-3xl md:text-5xl font-bold tracking-tighter mb-6">Exit the Loop.</h2>
            <p className="text-slate-400 mb-10 text-lg font-mono">Join the autonomous economy.</p>
            <TacticalButton>Initialize Swarm</TacticalButton>
          </motion.div>
        </div>
      </section>

      {/* Bottom Floating Nav */}
      <motion.nav
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, delay: 1 }}
        className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40"
      >
        <div className="flex items-center gap-1 bg-black/80 backdrop-blur-xl border border-white/20 px-4 py-2 rounded-full">
          <a
            href="#protocol"
            className="px-4 py-2 text-[10px] font-mono tracking-widest text-slate-400 hover:text-white transition-colors uppercase"
          >
            Protocol
          </a>
          <div className="w-px h-4 bg-white/20" />
          <a
            href="#velocity"
            className="px-4 py-2 text-[10px] font-mono tracking-widest text-slate-400 hover:text-white transition-colors uppercase"
          >
            Velocity
          </a>
          <div className="w-px h-4 bg-white/20" />
          <a
            href="#prime"
            className="px-4 py-2 text-[10px] font-mono tracking-widest text-slate-400 hover:text-white transition-colors uppercase"
          >
            Prime
          </a>
          <div className="w-px h-4 bg-white/20" />
          <div className="pl-2">
            <div className="flex items-center gap-1">
              <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse" />
              <span className="text-[9px] font-mono text-slate-600">LIVE</span>
            </div>
          </div>
        </div>
      </motion.nav>
    </div>
  );
}
