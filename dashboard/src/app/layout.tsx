import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TruthLayer — AI Hallucination Verification",
  description: "Real-time AI hallucination firewall. Verify AI outputs against source documents in under 100ms.",
  keywords: ["AI", "hallucination", "verification", "trust", "LLM", "fact-checking"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
