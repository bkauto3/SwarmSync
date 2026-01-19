import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SwarmSync — Zero-Touch Economy",
  description: "Obsidian & Liquid Chrome landing page theme for autonomous agent operations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <div className="noise-overlay" aria-hidden="true" />
      </body>
    </html>
  );
}
