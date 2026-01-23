'use client';

import { Menu } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { useNavbarMenu } from '@/hooks/use-navbar-menu';
import { cn } from '@/lib/utils';
import { navActiveStyles, navLinkClass, navLinks } from './navbar-constants';

export function Navbar() {
  const pathname = usePathname();
  const { isAuthenticated, logout } = useAuth();
  const { open, setOpen, menuRef, menuButtonRef } = useNavbarMenu();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border-base)] bg-[var(--surface-base)]/90 backdrop-blur">
      {/* Skip Navigation Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-[var(--accent-primary)] focus:px-4 focus:py-2 focus:text-white focus:outline-none focus:ring-2 focus:ring-white"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        {/* Logo - Top Left (Standard Convention) */}
        <Link href="/" className="flex items-center gap-4 group flex-shrink-0" aria-label="Swarm Sync homepage">
          <Image
            src="/logos/swarm-sync-purple.png"
            alt="Swarm Sync logo"
            width={64}
            height={64}
            priority
            quality={75}
            className="h-10 w-auto md:h-11 transition-transform duration-300 group-hover:scale-105 motion-reduce:transition-none motion-reduce:hover:transform-none"
            style={{ willChange: 'transform' }}
          />
        </Link>

        {/* Desktop Navigation - Adjacent to Logo */}
        <nav className="hidden md:flex items-center gap-8 ml-12 font-ui" aria-label="Main navigation">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              className={cn(
                navLinkClass,
                pathname.startsWith(link.href)
                  ? navActiveStyles
                  : 'hover:text-[var(--text-primary)]',
              )}
              href={link.href}
              aria-current={pathname.startsWith(link.href) ? 'page' : undefined}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Desktop Auth Actions - Right Side */}
        <div className="hidden items-center gap-4 md:flex ml-auto">
          {isAuthenticated ? (
            <>
              <button
                onClick={logout}
                className="text-sm font-medium uppercase tracking-wide text-[var(--text-secondary)] transition hover:text-[var(--text-primary)] font-ui min-h-[44px] px-3"
              >
                Sign out
              </button>
              <Button className="px-4 py-2 text-sm font-semibold min-h-[44px]" asChild>
                <Link href="/dashboard">Console</Link>
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" asChild className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] font-ui min-h-[44px]">
                <Link href="/login">Sign in</Link>
              </Button>
              <Button className="px-4 py-2 text-sm font-semibold min-h-[44px]" asChild>
                <Link href="/register">Get Started</Link>
              </Button>
            </>
          )}
        </div>

        {/* Mobile Menu Button */}
        <button
          ref={menuButtonRef}
          type="button"
          className="inline-flex rounded-full border border-border p-2 min-h-[44px] min-w-[44px] md:hidden items-center justify-center"
          onClick={() => setOpen((prev) => !prev)}
          aria-label={open ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={open}
          aria-controls="mobile-navigation"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      {/* Mobile Navigation Drawer */}
      {open && (
        <div
          ref={menuRef}
          id="mobile-navigation"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
          className="border-t border-[var(--border-base)] bg-[var(--surface-base)]/90 px-4 py-4 md:hidden"
        >
          <nav className="flex flex-col gap-4 text-sm" aria-label="Mobile navigation">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={cn(
                  'font-medium text-[var(--text-secondary)] min-h-[44px] flex items-center font-ui',
                  pathname.startsWith(link.href) && 'text-[var(--accent-primary)]',
                )}
                aria-current={pathname.startsWith(link.href) ? 'page' : undefined}
              >
                {link.label}
              </Link>
            ))}
            <div className="flex flex-col gap-3 mt-2">
              {isAuthenticated ? (
                <>
                  <Button variant="outline" onClick={logout} className="min-h-[44px]">
                    Sign out
                  </Button>
                  <Button asChild className="min-h-[44px]">
                    <Link href="/dashboard">Console</Link>
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="ghost" asChild className="min-h-[44px]">
                    <Link href="/login">Sign in</Link>
                  </Button>
                  <Button asChild className="min-h-[44px]">
                    <Link href="/register">Get Started</Link>
                  </Button>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
