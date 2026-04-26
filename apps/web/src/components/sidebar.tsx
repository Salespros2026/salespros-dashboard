"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { BarChart3, Megaphone, Layers, Image as ImageIcon, GitBranch } from "lucide-react";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/campaigns", label: "Kampanie", icon: Megaphone },
  { href: "/adsets", label: "Adsety", icon: Layers },
  { href: "/creatives", label: "Kreacje", icon: ImageIcon },
  { href: "/funnel", label: "Pipeline", icon: GitBranch },
];

export function Sidebar() {
  const pathname = usePathname();
  const search = useSearchParams();
  const qs = search.toString();

  return (
    <aside className="hidden lg:flex w-56 flex-col border-r border-border bg-sidebar text-sidebar-foreground py-6 px-3">
      <Link href={qs ? `/?${qs}` : "/"} className="px-3 mb-8 flex items-center gap-2">
        <div className="w-8 h-8 rounded-md bg-gradient-to-br from-emerald-500 to-blue-500 flex items-center justify-center text-white font-bold">
          S
        </div>
        <div>
          <div className="font-semibold tracking-tight">Salespros</div>
          <div className="text-xs text-muted-foreground">Dashboard</div>
        </div>
      </Link>
      <nav className="flex-1 flex flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          const fullHref = qs ? `${href}?${qs}` : href;
          return (
            <Link
              key={href}
              href={fullHref}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-3 pt-4 text-[10px] text-muted-foreground/60 leading-relaxed">
        Real CPL = spend / GHL leady (ghosts odfiltrowane).
        Meta CPL ≈ 3× zawyżony — porównaj.
      </div>
    </aside>
  );
}
