import Link from 'next/link';
import type { ReactNode } from 'react';

type Props = {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'muted' | 'ghost';
  href?: string;
  className?: string;
} & React.AnchorHTMLAttributes<HTMLAnchorElement>;

export function TacticalButton({ children, variant = 'primary', href, className, ...props }: Props) {
  const classes = ['tactical-button', variant, className].filter(Boolean).join(' ');

  if (href) {
    return (
      <Link href={href} className={classes} {...props}>
        {children}
      </Link>
    );
  }

  return (
    <button type="button" className={classes}>
      {children}
    </button>
  );
}
