"use client";

import { useEffect, useRef } from "react";

type Node = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  pulseIntensity: number;
};

export default function ChromeNetworkBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const nodesRef = useRef<Node[]>([]);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resizeCanvas = () => {
      const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      canvas.width = Math.floor(window.innerWidth * dpr);
      canvas.height = Math.floor(window.innerHeight * dpr);
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Initialize nodes
    const nodeCount = 45;
    nodesRef.current = Array.from({ length: nodeCount }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 2 + 1.5,
      pulseIntensity: 0,
    }));

    let lastPulseTime = Date.now();

    const animate = () => {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      const nodes = nodesRef.current;
      const currentTime = Date.now();

      // Global pulse every 3 seconds
      if (currentTime - lastPulseTime >= 3000) {
        lastPulseTime = currentTime;
        nodes.forEach((node) => (node.pulseIntensity = 1));
      }

      // Update and draw nodes
      nodes.forEach((node, i) => {
        node.x += node.vx;
        node.y += node.vy;

        if (node.x < 0 || node.x > window.innerWidth) node.vx *= -1;
        if (node.y < 0 || node.y > window.innerHeight) node.vy *= -1;

        if (node.pulseIntensity > 0) node.pulseIntensity -= 0.05;

        // Connections with pulse effect
        nodes.slice(i + 1).forEach((otherNode) => {
          const dx = node.x - otherNode.x;
          const dy = node.y - otherNode.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 180) {
            const baseOpacity = (1 - distance / 180) * 0.2;
            const pulseBoost = Math.max(node.pulseIntensity, otherNode.pulseIntensity) * 0.5;
            const lineWidth = 0.5 + Math.max(node.pulseIntensity, otherNode.pulseIntensity) * 2;

            ctx.beginPath();
            ctx.strokeStyle = `rgba(255, 255, 255, ${baseOpacity + pulseBoost})`;
            ctx.lineWidth = lineWidth;
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(otherNode.x, otherNode.y);
            ctx.stroke();
          }
        });

        // Node with glow + pulse
        const nodeGlow = 10 + node.pulseIntensity * 20;
        const nodeOpacity = 0.8 + node.pulseIntensity * 0.2;

        ctx.save();
        ctx.shadowColor = `rgba(255, 255, 255, ${nodeOpacity})`;
        ctx.shadowBlur = nodeGlow;

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.pulseIntensity > 0.5 ? "#FFFFFF" : "#94A3B8";
        ctx.fill();

        ctx.restore();
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}
