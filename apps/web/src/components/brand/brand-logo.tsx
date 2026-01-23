import Image from 'next/image';
import Link from 'next/link';

import { cn } from '@/lib/utils';

interface BrandLogoProps {
  /**
   * Target render size in pixels (logo is square so width = height).
   */
  size?: number;
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
  alt?: string;
  variant?: 'default' | 'transparent';
  href?: string;
}

const LOGO_SRC_FINAL = '/logos/swarm-sync-purple.png';

export function BrandLogo({
  size = 256,
  width,
  height,
  className,
  priority = false,
  alt = 'Swarm Sync logo',
  variant = 'default',
  href = '/',
}: BrandLogoProps) {
  return (
    <Link href={href} aria-label="Swarm Sync homepage">
      <Image
        src={LOGO_SRC_FINAL}
        alt={alt}
        width={width || size}
        height={height || size}
        priority={priority}
        quality={75}
        className={cn('h-auto w-auto object-contain', className)}
      />
    </Link>
  );
}
