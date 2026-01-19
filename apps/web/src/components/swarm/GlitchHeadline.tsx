import type { ReactNode } from 'react';

type Props = {
  text?: string;
  label?: string;
  children?: ReactNode;
  className?: string;
};

export default function GlitchHeadline({ text, label, children, className = "" }: Props) {
  // Extract plain text from children for data-text attribute (used by glitch effect)
  const getTextContent = (node: ReactNode): string => {
    if (typeof node === 'string') return node;
    if (typeof node === 'number') return String(node);
    if (Array.isArray(node)) return node.map(getTextContent).join('');
    if (node && typeof node === 'object' && 'props' in node) {
      return getTextContent((node as any).props?.children || '');
    }
    return '';
  };

  const content = children ?? text;
  const displayText = text || getTextContent(children) || '';
  const headlineClass = ['glitch-headline', className].filter(Boolean).join(' ');

  return (
    <div>
      {label && <p className="text-xs tracking-widest text-slate-500 uppercase mb-4">{label}</p>}
      <h1 className={headlineClass}>
        <span className="glitch-headline__text">{content}</span>
      </h1>
    </div>
  );
}
