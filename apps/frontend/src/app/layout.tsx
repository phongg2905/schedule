import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Manrope } from "next/font/google";

import "@/app/globals.css";
import { AppShell } from "@/components/layout/app-shell";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
});

export const metadata: Metadata = {
  title: "AI Planner",
  description: "AI companion for planning, adjustment, and behavior tracking.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={manrope.variable}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
