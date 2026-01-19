export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[9999] focus:px-4 focus:py-2 focus:bg-white focus:text-black focus:rounded-md focus:shadow-lg focus:font-semibold focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
    >
      Skip to main content
    </a>
  );
}
