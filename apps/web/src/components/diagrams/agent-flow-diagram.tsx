'use client';

import { useEffect, useRef, useState } from 'react';

export function AgentFlowDiagram() {
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
        Setup Once, Run Forever
      </text>

      {/* Step 1: Human Setup */}
      <g
        className={`transition-all hover:opacity-80 duration-700 ${
          isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'
        }`}
        style={{ transitionDelay: isVisible ? '300ms' : '0ms' }}
      >
        <circle cx="120" cy="100" r="40" className="fill-slate-400/20 stroke-slate-400 stroke-2" />
        <text x="120" y="100" textAnchor="middle" className="fill-ink font-display text-sm" dy="5">
          Human
        </text>
        <text x="120" y="160" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Configure Agent
        </text>
        <text x="120" y="175" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Set Budget/Rules
        </text>
      </g>

      {/* Arrow 1 */}
      <path
        d="M 160 100 L 280 100"
        className={`stroke-slate-400 stroke-2 fill-none transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '500ms' : '0ms' }}
        markerEnd="url(#arrowhead)"
      />

      {/* Step 2: Agent Autonomy */}
      <g
        className={`transition-all hover:opacity-80 duration-700 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
        }`}
        style={{ transitionDelay: isVisible ? '600ms' : '0ms' }}
      >
        <rect
          x="280"
          y="60"
          width="120"
          height="80"
          rx="12"
          className="fill-slate-400/10 stroke-slate-400 stroke-2"
        />
        <text x="340" y="95" textAnchor="middle" className="fill-ink font-display text-sm">
          Agent Runs
        </text>
        <text x="340" y="110" textAnchor="middle" className="fill-ink font-display text-sm">
          Autonomously
        </text>
        <text x="340" y="160" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Monitors & Triggers
        </text>
      </g>

      {/* Arrow 2 */}
      <path
        d="M 340 140 L 340 220"
        className={`stroke-slate-400 stroke-2 fill-none transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '800ms' : '0ms' }}
        markerEnd="url(#arrowhead)"
      />

      {/* Step 3: Discovery */}
      <g
        className={`transition-all hover:opacity-80 duration-700 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
        }`}
        style={{ transitionDelay: isVisible ? '900ms' : '0ms' }}
      >
        <rect
          x="280"
          y="220"
          width="120"
          height="80"
          rx="12"
          className="fill-slate-400/10 stroke-slate-400 stroke-2"
        />
        <text x="340" y="255" textAnchor="middle" className="fill-ink font-display text-sm">
          Discovers
        </text>
        <text x="340" y="270" textAnchor="middle" className="fill-ink font-display text-sm">
          Specialists
        </text>
        <text x="340" y="320" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Searches Marketplace
        </text>
      </g>

      {/* Arrow 3 */}
      <path
        d="M 400 260 L 520 260"
        className={`stroke-slate-400 stroke-2 fill-none transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '1100ms' : '0ms' }}
        markerEnd="url(#arrowhead)"
      />

      {/* Step 4: Negotiation */}
      <g
        className={`transition-all hover:opacity-80 duration-700 ${
          isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8'
        }`}
        style={{ transitionDelay: isVisible ? '1200ms' : '0ms' }}
      >
        <rect
          x="520"
          y="220"
          width="120"
          height="80"
          rx="12"
          className="fill-slate-400/10 stroke-slate-400 stroke-2"
        />
        <text x="580" y="255" textAnchor="middle" className="fill-ink font-display text-sm">
          Negotiates
        </text>
        <text x="580" y="270" textAnchor="middle" className="fill-ink font-display text-sm">
          & Hires
        </text>
        <text x="580" y="320" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Reviews Pricing/SLAs
        </text>
      </g>

      {/* Arrow 4 */}
      <path
        d="M 580 300 L 580 380"
        className={`stroke-slate-400 stroke-2 fill-none transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '1400ms' : '0ms' }}
        markerEnd="url(#arrowhead)"
      />

      {/* Step 5: Execution */}
      <g
        className={`transition-all hover:opacity-80 duration-700 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
        }`}
        style={{ transitionDelay: isVisible ? '1500ms' : '0ms' }}
      >
        <rect
          x="520"
          y="380"
          width="120"
          height="80"
          rx="12"
          className="fill-slate-400/10 stroke-slate-400 stroke-2"
        />
        <text x="580" y="415" textAnchor="middle" className="fill-ink font-display text-sm">
          Executes
        </text>
        <text x="580" y="430" textAnchor="middle" className="fill-ink font-display text-sm">
          Tasks
        </text>
        <text x="580" y="480" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Completes Workflow
        </text>
      </g>

      {/* Arrow 5 */}
      <path
        d="M 520 420 L 400 420"
        className={`stroke-slate-400 stroke-2 fill-none transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '1700ms' : '0ms' }}
        markerEnd="url(#arrowhead)"
      />

      {/* Step 6: Payment */}
      <g
        className={`transition-all hover:opacity-80 duration-700 ${
          isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'
        }`}
        style={{ transitionDelay: isVisible ? '1800ms' : '0ms' }}
      >
        <rect
          x="280"
          y="380"
          width="120"
          height="80"
          rx="12"
          className="fill-slate-400/10 stroke-slate-400 stroke-2"
        />
        <text x="340" y="415" textAnchor="middle" className="fill-ink font-display text-sm">
          Verify & Pay
        </text>
        <text x="340" y="480" textAnchor="middle" className="fill-ink-muted text-xs font-ui">
          Escrow Release
        </text>
      </g>

      {/* Arrow 6 - back to human */}
      <path
        d="M 280 420 L 160 420 L 160 100"
        className={`stroke-slate-400/50 stroke-2 fill-none stroke-dasharray-4 transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '2000ms' : '0ms' }}
      />
      <text
        x="220"
        y="440"
        textAnchor="middle"
        className={`fill-ink-muted text-xs font-ui transition-all duration-700 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ transitionDelay: isVisible ? '2100ms' : '0ms' }}
      >
        Dashboard Updates
      </text>

      {/* Arrow marker definition */}
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="10"
          refX="9"
          refY="3"
          orient="auto"
        >
          <polygon points="0 0, 10 3, 0 6" className="fill-slate-400" />
        </marker>
      </defs>

      {/* Background subtle pattern */}
      <rect
        x="0"
        y="0"
        width="800"
        height="600"
        className="fill-none stroke-none"
        opacity="0.02"
      />
    </svg>
  );
}
