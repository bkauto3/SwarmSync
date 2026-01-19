"use client";

import React, { useEffect, useRef } from "react";
import { usePrefersReducedMotion } from "@/components/usePrefersReducedMotion";

type Node = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

export function ChromeNetworkBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const nodesRef = useRef<Node[]>([]);
  const runningRef = useRef(true);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const baseNodeCount = 45;
    const linkDistance = 180;
    const maxSpeed = 0.45;

    const getNodeCount = () => {
      // Lighter load on mobile
      const w = window.innerWidth;
      return w < 640 ? 26 : baseNodeCount;
    };

    const resize = () => {
      const dpr = clamp(window.devicePixelRatio || 1, 1, 2);
      const w = window.innerWidth;
      const h = window.innerHeight;

      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const init = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;

      const nodeCount = getNodeCount();
      nodesRef.current = Array.from({ length: nodeCount }).map(() => {
        const angle = Math.random() * Math.PI * 2;
        const speed = 0.15 + Math.random() * maxSpeed;
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          r: 1.4 + Math.random() * 1.8,
        };
      });
    };

    const step = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;

      ctx.clearRect(0, 0, w, h);

      // Connections
      ctx.lineWidth = 1;
      for (let i = 0; i < nodesRef.current.length; i++) {
        const a = nodesRef.current[i];
        for (let j = i + 1; j < nodesRef.current.length; j++) {
          const b = nodesRef.current[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist <= linkDistance) {
            const t = 1 - dist / linkDistance;
            ctx.strokeStyle = `rgba(255,255,255,${0.06 + t * 0.14})`; // <= white-hot line
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // Nodes
      for (const n of nodesRef.current) {
        if (!reducedMotion && runningRef.current) {
          n.x += n.vx;
          n.y += n.vy;

          if (n.x <= 0 || n.x >= w) n.vx *= -1;
          if (n.y <= 0 || n.y >= h) n.vy *= -1;

          n.x = clamp(n.x, 0, w);
          n.y = clamp(n.y, 0, h);
        }

        ctx.save();
        ctx.shadowColor = "rgba(255,255,255,0.9)";
        ctx.shadowBlur = 10; // 0 0 10px white shadow
        ctx.fillStyle = "rgba(148,163,184,0.95)"; // chrome node core (#94A3B8)

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();

        // hot highlight
        ctx.shadowBlur = 0;
        ctx.fillStyle = "rgba(255,255,255,0.75)";
        ctx.beginPath();
        ctx.arc(n.x - n.r * 0.3, n.y - n.r * 0.3, Math.max(0.6, n.r * 0.35), 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
      }

      rafRef.current = window.requestAnimationFrame(step);
    };

    const onVisibility = () => {
      runningRef.current = document.visibilityState === "visible";
    };

    // init
    resize();
    init();
    runningRef.current = document.visibilityState === "visible";
    document.addEventListener("visibilitychange", onVisibility);

    // debounced resize
    let t: number | null = null;
    const onResize = () => {
      if (t) window.clearTimeout(t);
      t = window.setTimeout(() => {
        resize();
        init();
      }, 120);
    };
    window.addEventListener("resize", onResize);

    rafRef.current = window.requestAnimationFrame(step);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
      if (t) window.clearTimeout(t);
    };
  }, [reducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0 pointer-events-none opacity-80"
      aria-hidden="true"
    />
  );
}
