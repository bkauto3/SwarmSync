"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export default function GlitchHeadline({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const [isGlitching, setIsGlitching] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setIsGlitching(false), 500);
    return () => clearTimeout(timer);
  }, []);

  const gradientStyle: React.CSSProperties = {
    background: "linear-gradient(135deg, #94A3B8 0%, #E2E8F0 25%, #FFFFFF 50%, #E2E8F0 75%, #94A3B8 100%)",
    backgroundSize: "200% 200%",
    backgroundClip: "text",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  };

  return (
    <motion.h1
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className={className}
      style={{ ...gradientStyle, backgroundPosition: "0% 50%" }}
    >
      {isGlitching ? (
        <motion.span
          animate={{ opacity: [1, 0.3, 1, 0.5, 1, 0.2, 1], x: [0, -2, 2, -1, 1, 0] }}
          transition={{ duration: 0.5, times: [0, 0.1, 0.2, 0.4, 0.6, 0.8, 1] }}
        >
          {children}
        </motion.span>
      ) : (
        <motion.span
          animate={{ backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"] }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
          style={gradientStyle}
        >
          {children}
        </motion.span>
      )}
    </motion.h1>
  );
}
