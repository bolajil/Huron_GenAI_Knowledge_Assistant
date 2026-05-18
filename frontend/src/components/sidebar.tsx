"use client";

import { useState } from "react";
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
} from "lucide-react";

interface SidebarProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Chat Assistant", href: "/dashboard/chat", icon: MessageSquare },
  { name: "Query Assistant", href: "/dashboard/query", icon: Search },
  { name: "Agent Assistant", href: "/dashboard/agent", icon: Bot },
  { name: "Enhanced Research", href: "/dashboard/research", icon: Microscope },
  { name: "Document Ingest", href: "/dashboard/ingest", icon: FileUp },
  { name: "Index Management", href: "/dashboard/indexes", icon: Database },
  { name: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
];

const toolsNavigation = [
  { name: "System Monitoring", href: "/dashboard/monitoring", icon: Activity },
  { name: "MCP Dashboard", href: "/dashboard/mcp", icon: Plug },
  { name: "Feedback Analytics", href: "/dashboard/feedback", icon: ThumbsUp },
];

const adminNavigation = [
  { name: "Admin Panel", href: "/dashboard/admin", icon: Settings },
  { name: "Departments", href: "/dashboard/admin/departments", icon: Building2 },
  { name: "Users", href: "/dashboard/admin/users", icon: Users },
  { name: "Security", href: "/dashboard/admin/security", icon: Shield },
  { name: "Notifications", href: "/dashboard/admin/notifications", icon: Bell },
  { name: "Storage", href: "/dashboard/admin/storage", icon: HardDrive },
];

export function Sidebar({ open, setOpen }: SidebarProps) {
  const pathname = usePathname();

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
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">H</span>
          </div>
          {open && (
            <div className="flex flex-col">
              <span className="font-semibold text-sm">Huron</span>
              <span className="text-xs text-muted-foreground">Knowledge AI</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {open && (
          <span className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Main
          </span>
        )}
        {navigation.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== "/dashboard" && pathname?.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="w-5 h-5 shrink-0" />
              {open && <span className="text-sm font-medium">{item.name}</span>}
            </Link>
          );
        })}

        {/* Tools Section */}
        {open && (
          <span className="px-3 pt-6 text-xs font-medium text-muted-foreground uppercase tracking-wider block">
            Tools
          </span>
        )}
        {toolsNavigation.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="w-5 h-5 shrink-0" />
              {open && <span className="text-sm font-medium">{item.name}</span>}
            </Link>
          );
        })}

        {/* Admin Section */}
        {open && (
          <span className="px-3 pt-6 text-xs font-medium text-muted-foreground uppercase tracking-wider block">
            Admin
          </span>
        )}
        {adminNavigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="w-5 h-5 shrink-0" />
              {open && <span className="text-sm font-medium">{item.name}</span>}
            </Link>
          );
        })}
      </div>

      {/* Toggle Button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-center h-12 border-t border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        {open ? (
          <ChevronLeft className="w-5 h-5" />
        ) : (
          <ChevronRight className="w-5 h-5" />
        )}
      </button>
    </nav>
  );
}
