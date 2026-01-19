'use client';

import { useEffect, useRef, useState } from 'react';

export function AgentNetworkDiagram() {
  const containerRef = useRef<SVGSVGElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.2 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    };
  }, []);

  const specialists = [
    { x: 400, y: 100, label: 'Data Agent', icon: '📊' },
    { x: 600, y: 200, label: 'Analysis Agent', icon: '🔍' },
    { x: 600, y: 400, label: 'Content Agent', icon: '✍️' },
    { x: 400, y: 500, label: 'Code Agent', icon: '💻' },
    { x: 200, y: 400, label: 'API Agent', icon: '🔌' },
    { x: 200, y: 200, label: 'Research Agent', icon: '📚' },
  ];

  return (
    <svg
      ref={containerRef}
      viewBox="0 0 800 600"
      className={`mx-auto w-full max-w-4xl transition-opacity duration-1000 ${
        isVisible ? 'opacity-100' : 'opacity-0'
      }`}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Title */}
      <text
        x="400"
        y="30"
        textAnchor="middle"
        className={`fill-ink text-xl font-display transition-all duration-1000 delay-200 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'
        }`}
      >
        Your Agent Network
      </text>

      {/* Connection lines from orchestrator to specialists */}
      {specialists.map((spec, idx) => (
        <g key={idx}>
          {/* Connection line */}
          <line
            x1="400"
            y1="300"
            x2={spec.x}
            y2={spec.y}
            className={`stroke-slate-400/30 stroke-1 transition-all duration-700 ${
              isVisible ? 'opacity-100' : 'opacity-0'
            }`}
            style={{ transitionDelay: isVisible ? `${300 + idx * 100}ms` : '0ms' }}
            strokeDasharray="4 4"
          />

          {/* Flow indicators */}
          <text
            x={(400 + spec.x) / 2}
            y={(300 + spec.y) / 2}
            textAnchor="middle"
            className={`fill-slate-400/60 text-[10px] font-ui transition-all duration-700 ${
              isVisible ? 'opacity-100' : 'opacity-0'
            }`}
            style={{ transitionDelay: isVisible ? `${400 + idx * 100}ms` : '0ms' }}
          >
            hire • pay
          </text>
        </g>
      ))}

      {/* Central Orchestrator Agent */}
      <g
        className={`transition-all hover:scale-105 duration-700 ${
          isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
        }`}
        style={{ transitionDelay: isVisible ? '500ms' : '0ms' }}
      >
        <circle
          cx="400"
          cy="300"
          r="70"
          className="fill-slate-400/20 stroke-slate-400 stroke-3"
        />
        <text
          x="400"
          y="285"
          textAnchor="middle"
          className="fill-ink font-display text-lg"
        >
          🎯
        </text>
        <text
          x="400"
          y="305"
          textAnchor="middle"
          className="fill-ink font-display text-base"
        >
          Your
        </text>
        <text
          x="400"
          y="325"
          textAnchor="middle"
          className="fill-ink font-display text-base"
        >
          Orchestrator
        </text>
      </g>

      {/* Specialist Agents */}
      {specialists.map((spec, idx) => (
        <g
          key={idx}
          className={`transition-all hover:scale-110 duration-700 ${
            isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-90'
          }`}
          style={{ transitionDelay: isVisible ? `${600 + idx * 100}ms` : '0ms' }}
        >
          <circle
            cx={spec.x}
            cy={spec.y}
            r="50"
            className="fill-white stroke-slate-400/40 stroke-2"
          />
          <text
            x={spec.x}
            y={spec.y - 10}
            textAnchor="middle"
            className="fill-ink text-2xl"
          >
            {spec.icon}
          </text>
          <text
            x={spec.x}
            y={spec.y + 20}
            textAnchor="middle"
            className="fill-ink-muted font-ui text-xs"
          >
            {spec.label}
          </text>
        </g>
      ))}

      {/* Legend */}
      <g
        transform="translate(50, 550)"
        className={`transition-all duration-700 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
        }`}
        style={{ transitionDelay: isVisible ? '1300ms' : '0ms' }}
      >
        <line
          x1="0"
          y1="0"
          x2="30"
          y2="0"
          className="stroke-slate-400/30 stroke-1"
          strokeDasharray="4 4"
        />
        <text x="35" y="5" className="fill-ink-muted text-xs font-ui">
          Autonomous Discovery & Hiring
        </text>
      </g>
    </svg>
  );
}
