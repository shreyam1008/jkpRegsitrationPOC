import { LogIn, LogOut, Menu } from "lucide-react";
import { useAuthStore } from "@/stores/useAuthStore";
import { useSidebarStore } from "@/stores/useSidebarStore";

export function Header() {
  const { user, login, logout } = useAuthStore();
  const setOpen = useSidebarStore((s) => s.setOpen);

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-surface-glass px-4 py-3 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setOpen(true)}
          className="rounded-lg p-1.5 transition-colors hover:bg-hover md:hidden"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <span className="text-base font-semibold tracking-tight">JKP Registration POC</span>
      </div>

      {user ? (
        <div className="flex h-8 items-center gap-3">
          <div className="hidden items-center gap-1.5 text-xs text-muted md:flex">
            <span>{user.department}</span>
            <span>·</span>
            <span>{user.role}</span>
          </div>
          <span className="text-sm font-medium">{user.name}</span>
          <button
            onClick={logout}
            className="rounded-lg p-2 transition-colors hover:bg-hover"
            aria-label="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>
      ) : (
        <button
          onClick={() => login({ name: "Dev User", department: "IT", role: "Admin" })}
          className="flex h-8 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-medium text-on-primary transition-opacity hover:opacity-80"
        >
          Sign in
          <LogIn size={16} />
        </button>
      )}
    </header>
  );
}
