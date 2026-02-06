import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import { ShellBar } from "@/components/shell-bar";
import { PipelineNav } from "@/components/pipeline-nav";
import { DashboardSidebar } from "@/components/dashboard-sidebar";

import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Wybe Studio",
  description: "Robot learning pipeline — Datasets, Training, Simulation, Models",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <Providers>
          <ShellBar />
          <PipelineNav />
          <main className="min-h-[calc(100vh-7rem)]">{children}</main>
          <DashboardSidebar />
        </Providers>
      </body>
    </html>
  );
}
