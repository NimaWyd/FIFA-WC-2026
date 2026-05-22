"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  SignalIcon,
  TableCellsIcon,
  BoltIcon,
  TrophyIcon,
  UserGroupIcon,
} from "@heroicons/react/24/solid";

const TABS = [
  { label: "Live",     href: "/live",     Icon: SignalIcon,     isLive: true },
  { label: "Groups",   href: "/groups",   Icon: TableCellsIcon, isLive: false },
  { label: "Predict",  href: "/predict",  Icon: BoltIcon,       isLive: false },
  { label: "Simulate", href: "/simulate", Icon: TrophyIcon,     isLive: false },
  { label: "Teams",    href: "/teams",    Icon: UserGroupIcon,  isLive: false },
] as const;

export default function MobileBottomNav() {
  const pathname = usePathname();

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 md:hidden border-t border-white/[0.08] bg-navy-900/95 backdrop-blur-md"
      style={{ paddingBottom: "max(8px, env(safe-area-inset-bottom))" }}
      aria-label="Mobile navigation"
    >
      <div className="flex">
        {TABS.map(({ label, href, Icon, isLive }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex-1 flex flex-col items-center justify-center gap-1 pt-2.5 pb-1.5 min-h-[52px] transition-colors"
              aria-label={label}
              aria-current={active ? "page" : undefined}
            >
              <div className="relative">
                <Icon
                  className={`h-5 w-5 transition-colors ${
                    active ? "text-pitch-400" : "text-[rgba(240,236,226,0.38)]"
                  }`}
                />
                {isLive && (
                  <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                  </span>
                )}
              </div>
              <span
                className={`font-jb text-[9px] tracking-[0.06em] uppercase transition-colors ${
                  active ? "text-pitch-400" : "text-[rgba(240,236,226,0.32)]"
                }`}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
