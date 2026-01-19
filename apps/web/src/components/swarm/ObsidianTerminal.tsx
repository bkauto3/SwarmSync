type Props = {
  lines: string[];
  title?: string;
};

export default function ObsidianTerminal({ lines, title = 'Live Agent Feed' }: Props) {
  return (
    <div className="terminal-panel">
      <div className="terminal-header">{title}</div>
      <div className="terminal-body">
        {lines.map((line, index) => (
          <div key={`${line}-${index}`} className="terminal-line">
            <span>{line}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
