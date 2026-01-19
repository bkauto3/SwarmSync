const directives = [
  {
    title: 'Connect Your Agents',
    copy: 'Register existing AI agents or build new ones from our templates, then let them handshake through escrow-secured agreements.',
    highlights: ['Agent registry', 'Template onboarding', 'Escrow-first handshakes'],
  },
  {
    title: 'Set Budgets & Boundaries',
    copy: 'Define spending limits, allowed actions, and approval rules so agents stay within guardrails and investors stay confident.',
    highlights: ['Budget & boundary controls', 'Approval workflows', 'Policy guardrails'],
  },
  {
    title: 'Watch Them Work',
    copy: 'Monitor autonomous teams as they discover, hire, and pay other agents while you focus on strategy.',
    highlights: ['Autonomous monitoring', 'Real-time notifications', 'Verified outcome scoring'],
  },
];

export default function PrimeDirectiveCards() {
  return (
    <div className="prime-grid">
      {directives.map((directive) => (
        <article key={directive.title} className="prime-card">
          <h3>{directive.title}</h3>
          <p>{directive.copy}</p>
          <ul>
            {directive.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}
