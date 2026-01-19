"use client";

import Link from 'next/link';
import { Button } from '@/components/ui/button';

// Mock data
const agents = [
  {
    id: '1',
    name: 'DataCleanerBot',
    status: 'Under Review',
    category: 'Research',
    submittedAt: '2024-01-15',
  },
];

const statusColors: Record<string, string> = {
  'Under Review': 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300',
  'Live': 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  'Rejected': 'border-red-500/40 bg-red-500/10 text-red-300',
  'Paused': 'border-slate-500/40 bg-slate-500/10 text-slate-300',
};

export default function ProviderAgentsPage() {
  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-display text-white mb-2">Your Agents</h1>
            <p className="text-[var(--text-secondary)]">Manage all your listed agents</p>
          </div>
          <Link href="/dashboard/provider/agents/new">
            <Button>Add New Agent</Button>
          </Link>
        </div>

        {agents.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-12 text-center">
            <p className="text-lg text-[var(--text-secondary)] mb-4">You haven't created any agents yet.</p>
            <Link href="/dashboard/provider/agents/new">
              <Button>Create Your First Agent</Button>
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-white/10">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Agent Name</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Category</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Submitted</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-white">Actions</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr key={agent.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-6 py-4 text-white font-medium">{agent.name}</td>
                    <td className="px-6 py-4 text-[var(--text-secondary)]">{agent.category}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${statusColors[agent.status] || statusColors['Under Review']}`}>
                        {agent.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-[var(--text-secondary)]">{agent.submittedAt}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/dashboard/provider/agents/${agent.id}`}>
                          <Button variant="outline" size="sm">View</Button>
                        </Link>
                        <Link href={`/dashboard/provider/agents/${agent.id}/edit`}>
                          <Button variant="ghost" size="sm">Edit</Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

