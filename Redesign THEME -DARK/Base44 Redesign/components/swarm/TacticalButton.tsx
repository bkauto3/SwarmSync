"use client";

import { motion } from "framer-motion";
import { useState } from "react";

export default function TacticalButton({
  children,
  variant = "primary",
  onClick,
  className = "",
}: {
  children: React.ReactNode;
  variant?: "primary" | "ghost";
  onClick?: () => void;
  className?: string;
}) {
  const [isHovered, setIsHovered] = useState(false);

  const Brackets = ({ z = "z-20" }: { z?: string }) => (
    <>
      <motion.span
        className={`absolute top-0 left-0 w-2 h-2 border-t border-l border-white ${z}`}
        initial={{ x: 4, y: 4, opacity: 0 }}
        animate={isHovered ? { x: 0, y: 0, opacity: 1 } : { x: 4, y: 4, opacity: 0 }}
        transition={{ duration: 0.2 }}
      />
      <motion.span
        className={`absolute top-0 right-0 w-2 h-2 border-t border-r border-white ${z}`}
        initial={{ x: -4, y: 4, opacity: 0 }}
        animate={isHovered ? { x: 0, y: 0, opacity: 1 } : { x: -4, y: 4, opacity: 0 }}
        transition={{ duration: 0.2 }}
      />
      <motion.span
        className={`absolute bottom-0 left-0 w-2 h-2 border-b border-l border-white ${z}`}
        initial={{ x: 4, y: -4, opacity: 0 }}
        animate={isHovered ? { x: 0, y: 0, opacity: 1 } : { x: 4, y: -4, opacity: 0 }}
        transition={{ duration: 0.2 }}
      />
      <motion.span
        className={`absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white ${z}`}
        initial={{ x: -4, y: -4, opacity: 0 }}
        animate={isHovered ? { x: 0, y: 0, opacity: 1 } : { x: -4, y: -4, opacity: 0 }}
        transition={{ duration: 0.2 }}
      />
    </>
  );

  if (variant === "ghost") {
    return (
      <motion.button
        onClick={onClick}
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        whileTap={{ scale: 0.98 }}
        className={`
          relative px-6 py-3 text-xs font-mono tracking-wider uppercase
          border border-white/20 text-slate-300
          hover:border-white/40 hover:text-white
          transition-all duration-300
          backdrop-blur-sm
          ${className}
        `}
      >
        <Brackets z="z-10" />
        <span className="relative z-10">{children}</span>
      </motion.button>
    );
  }

  return (
    <motion.button
      onClick={onClick}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileTap={{ scale: 0.98 }}
      className={`relative px-6 py-3 text-xs font-mono tracking-wider uppercase overflow-hidden ${className}`}
      style={{
        background: "linear-gradient(135deg, #64748B 0%, #94A3B8 25%, #CBD5E1 50%, #94A3B8 75%, #64748B 100%)",
        backgroundSize: "200% 200%",
      }}
    >
      <Brackets />
      <motion.div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(135deg, #94A3B8 0%, #E2E8F0 25%, #FFFFFF 50%, #E2E8F0 75%, #94A3B8 100%)",
          backgroundSize: "200% 200%",
        }}
        animate={{ backgroundPosition: ["0% 0%", "100% 100%", "0% 0%"] }}
        transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
      />
      <div
        className="absolute inset-0 transition-opacity duration-300"
        style={{
          opacity: isHovered ? 1 : 0,
          background: "white",
          boxShadow: "inset 0 0 30px rgba(255,255,255,0.5)",
        }}
      />
      <div
        className="absolute inset-0 opacity-60"
        style={{
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.4) 0%, transparent 40%, transparent 60%, rgba(0,0,0,0.1) 100%)",
        }}
      />
      <span className="relative z-10 text-slate-900">{children}</span>
    </motion.button>
  );
}
