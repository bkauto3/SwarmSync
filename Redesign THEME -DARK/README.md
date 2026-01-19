# SwarmSync — Obsidian & Liquid Chrome (Production Repo)

A Next.js + Tailwind + Framer Motion landing page implementing:

- Canvas "Chrome Network" background (drifting nodes + proximity links)
- Zero-Touch hero + glossy / ghost CTAs
- Animated Obsidian Terminal log
- Velocity Gap comparison grid with glowing divider
- Prime Directive glass cards

## Quickstart

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Build & Run

```bash
npm run build
npm run start
```

## Notes

- Canvas respects `prefers-reduced-motion`
- Animation pauses when the tab is hidden to save battery
- Mobile reduces node count for performance
