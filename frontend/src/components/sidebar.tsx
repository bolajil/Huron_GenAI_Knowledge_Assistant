"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "../utils/cn";
import {
  Home,
  MessageSquare,
  FileUp,
  Search,
  Users,
  Settings,
  Building2,
  BarChart3,
  Shield,
  ChevronLeft,
  ChevronRight,
  Bot,
  Microscope,
  Database,
  Activity,
  Plug,
  ThumbsUp,
  Bell,
  HardDrive,
  ClipboardList,
  Crown,
} from "lucide-react";
import { useAuth } from "../contexts/auth-context";
import type { UserRole } from "../services/api";

interface SidebarProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const ROLE_LABEL: Record<UserRole, string> = {
  root:       "Root",
  dept_admin: "Dept Admin",
  power_user: "Power User",
  user:       "User",
  viewer:     "Viewer",
};

const ROLE_COLOR: Record<UserRole, string> = {
  root:       "bg-red-500/15 text-red-600 dark:text-red-400",
  dept_admin: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  power_user: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  user:       "bg-green-500/15 text-green-600 dark:text-green-400",
  viewer:     "bg-gray-500/15 text-gray-500",
};

type RoleLevel = 1 | 2 | 3 | 4 | 5;
const ROLE_LEVEL: Record<UserRole, RoleLevel> = {
  viewer:     1,
  user:       2,
  power_user: 3,
  dept_admin: 4,
  root:       5,
};

function NavLink({
  href,
  icon: Icon,
  name,
  open,
  active,
}: {
  href: string;
  icon: React.ElementType;
  name: string;
  open: boolean;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
      )}
    >
      <Icon className="w-5 h-5 shrink-0" />
      {open && <span className="text-sm font-medium">{name}</span>}
    </Link>
  );
}

export function Sidebar({ open, setOpen }: SidebarProps) {
  const pathname = usePathname();
  const { user, isRoot, isDeptAdmin } = useAuth();

  const role = user?.role ?? "viewer";
  const level = ROLE_LEVEL[role] ?? 1;

  const isActive = (href: string) =>
    href === "/dashboard"
      ? pathname === href
      : pathname === href || pathname?.startsWith(href + "/");

  // ── Main nav — visible by minimum role level ────────────────────────────
  const mainNav = [
    { name: "Dashboard",         href: "/dashboard",          icon: Home,       minLevel: 1 },
    { name: "Chat Assistant",    href: "/dashboard/chat",     icon: MessageSquare, minLevel: 2 },
    { name: "Query Assistant",   href: "/dashboard/query",    icon: Search,     minLevel: 1 },
    { name: "Agent Assistant",   href: "/dashboard/agent",    icon: Bot,        minLevel: 3 },
    { name: "Enhanced Research", href: "/dashboard/research", icon: Microscope, minLevel: 3 },
    { name: "Document Ingest",   href: "/dashboard/ingest",   icon: FileUp,     minLevel: 3 },
    { name: "Index Management",  href: "/dashboard/indexes",  icon: Database,   minLevel: 5 },
    { name: "Analytics",         href: "/dashboard/analytics",icon: BarChart3,  minLevel: 4 },
  ].filter((item) => level >= item.minLevel);

  // ── Tools nav ───────────────────────────────────────────────────────────
  const toolsNav = [
    { name: "System Monitoring", href: "/dashboard/monitoring", icon: Activity, minLevel: 4 },
    { name: "MCP Dashboard",     href: "/dashboard/mcp",        icon: Plug,     minLevel: 5 },
    { name: "Feedback Analytics",href: "/dashboard/feedback",   icon: ThumbsUp, minLevel: 4 },
  ].filter((item) => level >= item.minLevel);

  // ── Admin nav ───────────────────────────────────────────────────────────
  const adminNav = [
    { name: "Admin Panel",     href: "/dashboard/admin",                 icon: Settings,     minLevel: 4 },
    { name: "Departments",     href: "/dashboard/admin/departments",      icon: Building2,    minLevel: 5 },
    { name: "Users",           href: "/dashboard/admin/users",           icon: Users,        minLevel: 4 },
    { name: "Access Requests", href: "/dashboard/admin/access-requests", icon: ClipboardList,minLevel: 1 },
    { name: "Security",        href: "/dashboard/admin/security",        icon: Shield,       minLevel: 5 },
    { name: "Notifications",   href: "/dashboard/admin/notifications",   icon: Bell,         minLevel: 4 },
    { name: "Storage",         href: "/dashboard/admin/storage",         icon: HardDrive,    minLevel: 5 },
  ].filter((item) => level >= item.minLevel);

  const showTools = toolsNav.length > 0;
  const showAdmin = adminNav.length > 0;

  return (
    <nav
      className={cn(
        "flex flex-col h-screen bg-card border-r border-border transition-all duration-300",
        open ? "w-64" : "w-16"
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <span className="text-primary-foreground font-bold text-sm">H</span>
          </div>
          {open && (
            <div className="flex flex-col min-w-0">
              <span className="font-semibold text-sm">Huron</span>
              <span className="text-xs text-muted-foreground">Knowledge AI</span>
            </div>
          )}
        </div>
      </div>

      {/* Role badge */}
      {open && user && (
        <div className="px-4 py-2 border-b border-border">
          <div className="flex items-center gap-2">
            {isRoot() && <Crown className="w-3.5 h-3.5 text-red-500 shrink-0" />}
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full font-medium",
                ROLE_COLOR[role] ?? ROLE_COLOR.viewer
              )}
            >
              {ROLE_LABEL[role] ?? role}
            </span>
            <span className="text-xs text-muted-foreground truncate">{user.username}</span>
          </div>
          {!isRoot() && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">
              Dept: {user.department}
            </p>
          )}
        </div>
      )}

      {/* Scrollable nav */}
      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {open && (
          <p className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Main
          </p>
        )}
        {mainNav.map((item) => (
          <NavLink key={item.href} {...item} open={open} active={isActive(item.href)} />
        ))}

        {showTools && (
          <>
            {open && (
              <p className="px-3 pt-5 pb-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Tools
              </p>
            )}
            {toolsNav.map((item) => (
              <NavLink key={item.href} {...item} open={open} active={isActive(item.href)} />
            ))}
          </>
        )}

        {showAdmin && (
          <>
            {open && (
              <p className="px-3 pt-5 pb-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {isDeptAdmin() ? "Admin" : "Account"}
              </p>
            )}
            {adminNav.map((item) => (
              <NavLink key={item.href} {...item} open={open} active={isActive(item.href)} />
            ))}
          </>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-center h-12 border-t border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        {open ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
      </button>
    </nav>
  );
}
