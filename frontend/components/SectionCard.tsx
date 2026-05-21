import { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  badge?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, badge, children }: SectionCardProps) {
  return (
    <section
      className="rounded-2xl p-5"
      style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{title}</h2>
        {badge}
      </div>
      {children}
    </section>
  );
}
