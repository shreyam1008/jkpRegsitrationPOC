import { Link, useRouterState } from "@tanstack/react-router";
import { ChevronLeft, X } from "lucide-react";
import { NAV_ITEMS } from "@/config/navigation";
import { useIsMobile } from "@/hooks/useIsMobile";
import { useSidebarStore } from "@/stores/useSidebarStore";

export function Sidebar() {
  const { isOpen, toggle, setOpen } = useSidebarStore();
  const currentPath = useRouterState({ select: (s) => s.location.pathname });
  const isMobile = useIsMobile();

  const closeMobile = () => { if (isMobile) setOpen(false); };

  return (
    <>
      {/* Backdrop — always in DOM for smooth fade transition, mobile only */}
      <div
        className={`fixed inset-0 z-40 bg-backdrop backdrop-blur-sm transition-opacity duration-300 md:hidden ${isOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setOpen(false)}
        aria-hidden="true"
      />

      {/* Sidebar panel */}
      <aside
        className={[
          "flex flex-col border-r transition-all duration-300 ease-out",
          // Mobile: fixed full-height drawer
          "fixed top-0 left-0 z-50 h-full w-72",
          isOpen ? "translate-x-0" : "-translate-x-full",
          // Desktop: static, collapsible width
          "md:static md:z-auto md:h-auto md:translate-x-0",
          isOpen ? "md:w-56" : "md:w-14",
          "border-border bg-surface-alt",
        ].join(" ")}
      >
        {/* Mobile drawer header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3 md:hidden">
          <span className="text-sm font-semibold tracking-tight">Menu</span>
          <button
            onClick={() => setOpen(false)}
            className="rounded-lg p-1.5 transition-colors hover:bg-hover"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Desktop top spacer */}
        <div className="hidden h-3 md:block" />

        {/* Nav items — scrollable when list grows */}
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 pt-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
            const active = currentPath === to;
            return (
              <Link
                key={to}
                to={to}
                onClick={closeMobile}
                className={[
                  "relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  !isOpen ? "md:justify-center md:px-0" : "",
                  active
                    ? "bg-active text-foreground"
                    : "text-muted hover:bg-hover hover:text-foreground",
                ].join(" ")}
                title={!isOpen ? label : undefined}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-current" />
                )}
                <Icon size={18} strokeWidth={active ? 2.25 : 1.75} />
                <span className={isOpen ? "" : "md:hidden"}>{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle — desktop only */}
        <button
          onClick={toggle}
          className={[
            "mx-2 mb-3 hidden items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors md:flex",
            !isOpen ? "justify-center" : "",
            "text-faint hover:bg-hover hover:text-foreground",
          ].join(" ")}
          aria-label="Toggle sidebar"
        >
          <ChevronLeft size={16} className={`transition-transform duration-200 ${!isOpen ? "rotate-180" : ""}`} />
          {isOpen && <span>Collapse</span>}
        </button>
      </aside>
    </>
  );
}
