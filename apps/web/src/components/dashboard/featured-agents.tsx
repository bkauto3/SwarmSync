"use client";

import { type Agent } from "@agent-market/sdk";
import Link from "next/link";
import { useMemo, useState } from "react";

interface FeaturedAgentsProps {
  agents: Agent[];
}

export function FeaturedAgents({ agents }: FeaturedAgentsProps) {
  const hasAgents = agents && agents.length > 0;
  const [selectedId, setSelectedId] = useState<string | null>(
    hasAgents ? agents[0]?.id ?? null : null,
  );

  const selectedAgent = useMemo(() => {
    if (!hasAgents || !selectedId) return null;
    return agents.find((a) => a.id === selectedId) ?? agents[0] ?? null;
  }, [agents, hasAgents, selectedId]);

  return (
    <div className="card space-y-4 p-6">
      <div>
        <h2 className="text-sm uppercase tracking-wide text-[var(--text-muted)] mb-1 font-ui">
          Featured agents
        </h2>
        <p className="text-xs text-[var(--text-muted)] font-ui">
          Pick an agent from the dropdown to see details. No long scrolling.
        </p>
      </div>
      {hasAgents ? (
        <div className="space-y-4">
          <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] font-ui">
            Choose an agent
          </label>
          <select
            value={selectedId ?? ""}
            onChange={(e) => setSelectedId(e.target.value)}
            className="w-full rounded-xl border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--border-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--shadow-focus)] font-ui"
          >
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}{" "}
                {agent.trustScore !== undefined ? `(Trust ${agent.trustScore})` : ""}
              </option>
            ))}
          </select>

          {selectedAgent && (
            <div className="card-inner rounded-xl border border-[var(--border-base)] p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-[var(--text-primary)] font-display">
                    {selectedAgent.name}
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] font-ui">{selectedAgent.slug}</p>
                </div>
                {selectedAgent.trustScore !== undefined && (
                  <span className="text-xs text-emerald-400 font-ui text-meta-numeric">
                    Trust {selectedAgent.trustScore}
                  </span>
                )}
              </div>
              <p className="mt-2 text-xs text-[var(--text-secondary)] font-ui">
                {selectedAgent.description || "No description provided."}
              </p>
              <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-muted)] font-ui">
                <span className="capitalize">
                  {selectedAgent.categories?.slice(0, 3).join(", ") || "Uncategorized"}
                </span>
                <Link className="text-[var(--text-secondary)] underline hover:text-[var(--text-primary)]" href={`/agents/${selectedAgent.slug}`}>
                  View profile
                </Link>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card-inner rounded-xl border border-[var(--border-base)] p-4 text-sm text-[var(--text-muted)] font-ui">
          No agents found. Create or import an agent to feature it here.
        </div>
      )}
    </div>
  );
}
