import { LanguageSwitch, useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Button, cn, EmptyState, Logo } from "@nirnoy/ui";
import {
  Boxes,
  Building2,
  CalendarDays,
  Coins,
  FileCheck2,
  FlaskConical,
  Handshake,
  Headphones,
  LayoutDashboard,
  LogOut,
  Menu,
  Microscope,
  QrCode,
  Receipt,
  ScrollText,
  ShieldCheck,
  ShieldOff,
  Truck,
  UsersRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  permission?: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "nav.groupOverview",
    items: [{ to: "/", label: "nav.dashboard", icon: LayoutDashboard }],
  },
  {
    label: "nav.groupOperations",
    items: [
      { to: "/bookings", label: "nav.bookings", icon: CalendarDays },
      { to: "/collections", label: "nav.collections", icon: Truck, permission: "collection:view" },
      { to: "/samples", label: "nav.samples", icon: QrCode, permission: "sample:view" },
      { to: "/lab", label: "nav.lab", icon: Microscope, permission: "lab:view" },
      { to: "/reports", label: "nav.reports", icon: FileCheck2 },
    ],
  },
  {
    label: "nav.groupBusiness",
    items: [
      { to: "/billing", label: "nav.billing", icon: Receipt },
      { to: "/inventory", label: "nav.inventory", icon: Boxes, permission: "inventory:view" },
      { to: "/finance", label: "nav.finance", icon: Coins, permission: "settings:manage" },
      { to: "/crm", label: "nav.crm", icon: Headphones },
      { to: "/corporate", label: "nav.corporate", icon: Building2, permission: "corporate:manage" },
      { to: "/partners", label: "nav.partners", icon: Handshake, permission: "partner:manage" },
    ],
  },
  {
    label: "nav.groupAdmin",
    items: [
      { to: "/catalog", label: "nav.catalog", icon: FlaskConical },
      { to: "/users", label: "nav.users", icon: UsersRound, permission: "user:manage" },
      { to: "/roles", label: "nav.roles", icon: ShieldCheck, permission: "role:manage" },
      { to: "/audit", label: "nav.audit", icon: ScrollText, permission: "audit:view" },
    ],
  },
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? (parts.at(-1)?.[0] ?? "") : "")).toUpperCase();
}

export function Shell() {
  const { t } = useTranslation("console");
  const { me, can, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  if (!me?.is_staff) {
    return (
      <div className="bg-dots flex min-h-dvh items-center justify-center p-4">
        <div className="flex flex-col items-center rounded-[var(--radius-xl)] border border-border bg-surface p-6 shadow-[var(--shadow-pop)]">
          <EmptyState
            icon={<ShieldOff className="size-6" aria-hidden="true" />}
            title={t("noAccess.title")}
            description={t("noAccess.body")}
          />
          <Button variant="secondary" onClick={() => void signOut()}>
            <LogOut aria-hidden="true" />
            {t("common:signOut")}
          </Button>
        </div>
      </div>
    );
  }

  // Menu shows only what the user may open; the API still checks every request.
  const groups = NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((item) => !item.permission || can(item.permission)),
  })).filter((g) => g.items.length > 0);

  const current = NAV_GROUPS.flatMap((g) => g.items).find((item) =>
    item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to),
  );
  const displayName = me.full_name ?? me.phone ?? "";
  const primaryRole = me.roles[0]?.role.replaceAll("_", " ").toLowerCase();

  const nav = (
    <nav aria-label={t("nav.menu")} className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 pb-4 pt-2">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 px-3 text-[11px] font-bold uppercase tracking-[0.12em] text-muted/80" aria-hidden="true">
            {t(group.label)}
          </p>
          <div className="flex flex-col gap-0.5">
            {group.items.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    "group relative flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2 text-sm font-medium",
                    isActive
                      ? "bg-brand-50 text-brand-700 before:absolute before:-left-3 before:top-1.5 before:bottom-1.5 before:w-1 before:rounded-r-full before:bg-brand-600"
                      : "text-muted hover:translate-x-0.5 hover:bg-surface-muted hover:text-fg",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        "flex size-7 items-center justify-center rounded-lg transition-colors",
                        isActive
                          ? "bg-gradient-brand text-white shadow-[var(--shadow-brand)] dark:text-bg"
                          : "bg-surface-muted text-muted group-hover:bg-brand-50 group-hover:text-brand-600",
                      )}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    {t(label)}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );

  const userCard = (
    <div className="m-3 flex items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/60 p-2.5">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-gradient-brand text-xs font-bold text-white dark:text-bg">
        {initials(displayName)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-fg">{displayName}</p>
        {primaryRole && <p className="truncate text-xs capitalize text-muted">{primaryRole}</p>}
      </div>
    </div>
  );

  return (
    <div className="flex min-h-dvh bg-bg">
      <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-border bg-surface lg:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Logo label={t("title")} />
        </div>
        {nav}
        {userCard}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 animate-fade-in bg-[color-mix(in_srgb,var(--brand-950)_45%,transparent)] backdrop-blur-sm"
            aria-label={t("common:close")}
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 animate-slide-in-left flex-col bg-surface shadow-[var(--shadow-pop)]">
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
              <Logo label={t("title")} />
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full hover:rotate-90"
                aria-label={t("common:close")}
                onClick={() => setMobileOpen(false)}
              >
                <X />
              </Button>
            </div>
            {nav}
            {userCard}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="glass sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-border px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full lg:hidden"
              aria-label={t("nav.menu")}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(true)}
            >
              <Menu />
            </Button>
            {current && (
              <p className="flex min-w-0 items-center gap-2 font-display text-base font-bold text-fg">
                <current.icon className="size-4.5 shrink-0 text-brand-600" aria-hidden="true" />
                <span className="truncate">{t(current.label)}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <LanguageSwitch className="hidden sm:inline-flex" />
            <span className="hidden h-6 w-px bg-border md:block" aria-hidden="true" />
            <span className="hidden items-center gap-2 md:flex">
              <span className="flex size-8 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700 ring-2 ring-brand-600/10">
                {initials(displayName)}
              </span>
              <span className="max-w-40 truncate text-sm font-medium text-fg">{displayName}</span>
            </span>
            <Button
              variant="secondary"
              size="sm"
              className="hover:border-danger/40 hover:bg-danger-bg hover:text-danger"
              onClick={async () => {
                await signOut();
                navigate("/login", { replace: true });
              }}
            >
              <LogOut aria-hidden="true" />
              <span className="hidden sm:inline">{t("common:signOut")}</span>
            </Button>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
