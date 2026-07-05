import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { AppShell } from "@/components/layout/app-shell";
import { IntlProvider } from "@/providers/intl-provider";

export const metadata: Metadata = {
  title: "Planner",
  description: "A calm schedule planner built around your tasks and activity.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <IntlProvider>
          <AppShell>{children}</AppShell>
        </IntlProvider>
      </body>
    </html>
  );
}
