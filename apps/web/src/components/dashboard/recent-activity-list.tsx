const recentActivity = [
  {
    label: 'Research Analyst run',
    status: 'Succeeded',
    timestamp: '2 minutes ago',
    spend: '$3.60',
  },
  {
    label: 'Workflow “Launch Plan”',
    status: 'Completed',
    timestamp: '1 hour ago',
    spend: '$12.40',
  },
  {
    label: 'Support Copilot',
    status: 'Queued',
    timestamp: 'Yesterday',
    spend: '$0.00',
  },
];

export function RecentActivityList() {
  return (
    <div className="card space-y-4 p-6 text-sm">
      <div>
        <h2 className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-1 font-ui">Recent activity</h2>
        <p className="text-xs text-[var(--text-muted)] font-ui">Latest runs + spend.</p>
      </div>
      <ul className="space-y-3">
        {recentActivity.map((item) => (
          <li
            key={item.label}
            className="card-inner rounded-xl border border-[var(--border-base)] px-4 py-3 text-sm"
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold text-[var(--text-primary)] font-ui">{item.label}</span>
              <span className="text-[var(--text-secondary)] font-ui text-meta-numeric">{item.spend}</span>
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-[var(--text-muted)] font-ui">
              <span>{item.status}</span>
              <span className="text-meta-numeric">{item.timestamp}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
