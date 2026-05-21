import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "TaskInsight",
  description: "Redmine 데이터 기반 팀 흐름 분석 플랫폼",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full">
      <body className="min-h-full flex" style={{ backgroundColor: "var(--background)" }}>
        <Sidebar />
        <main
          className="flex-1 min-h-screen"
          style={{ marginLeft: "var(--sidebar-width)" }}
        >
          {children}
        </main>
      </body>
    </html>
  );
}
