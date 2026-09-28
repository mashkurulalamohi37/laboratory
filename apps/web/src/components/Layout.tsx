import { LanguageSwitch, useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Button, cn, Logo } from "@nirnoy/ui";
import {
  ArrowRight,
  Award,
  Building2,
  HeartPulse,
  Mail,
  MapPin,
  Menu,
  Package,
  Phone,
  ShieldCheck,
  TestTube2,
  UserRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, ScrollRestoration, useLocation } from "react-router";
import { CartDrawer } from "./CartDrawer";

interface NavItem {
  to: string;
  labelKey: string;
  fallback: string;
  icon: LucideIcon;
}

const NAV: NavItem[] = [
  { to: "/tests", labelKey: "nav.tests", fallback: "Tests", icon: TestTube2 },
  { to: "/packages", labelKey: "nav.packages", fallback: "Packages", icon: Package },
  { to: "/concerns", labelKey: "nav.concerns", fallback: "Health Concerns", icon: HeartPulse },
  { to: "/centres", labelKey: "nav.centres", fallback: "Centres", icon: Building2 },
];

export function Layout() {
  const { t } = useTranslation();
  const { status } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("skipToContent", "Skip to content")}
      </a>
      <header
        className={cn(
          "glass sticky top-0 z-30 border-b transition-[border-color,box-shadow] duration-300",
          scrolled ? "border-border shadow-[var(--shadow-card)]" : "border-transparent",
        )}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:h-[72px]">
          <div className="flex items-center gap-8">
            <Link to="/" className="rounded-lg">
              <Logo label={t("brand", "Nirnoy Diagnostics")} />
            </Link>
            <nav aria-label={t("nav.main", "Main")} className="hidden items-center gap-1 lg:flex">
              {NAV.map(({ to, labelKey, fallback, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "group relative flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-medium",
                      isActive
                        ? "bg-brand-50 text-brand-700"
                        : "text-muted hover:bg-surface-muted hover:text-fg",
                    )
                  }
                >
                  <Icon className="size-4 text-brand-600 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:scale-110" />
                  <span>{t(labelKey, fallback)}</span>
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2.5">
            <CartDrawer />
            <LanguageSwitch className="hidden sm:inline-flex" />
            {status === "authenticated" ? (
              <Button asChild variant="secondary" size="sm" className="hidden sm:inline-flex">
                <Link to="/account">
                  <UserRound aria-hidden="true" className="size-4" />
                  <span>{t("account", "Account")}</span>
                </Link>
              </Button>
            ) : (
              <Button asChild size="sm" className="hidden sm:inline-flex">
                <Link to="/login">
                  {t("signIn", "Sign in")}
                  <ArrowRight className="transition-transform group-hover/btn:translate-x-0.5" />
                </Link>
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full lg:hidden"
              aria-label={menuOpen ? t("close", "Close") : t("nav.menu", "Menu")}
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
              onClick={() => setMenuOpen((o) => !o)}
            >
              {menuOpen ? <X /> : <Menu />}
            </Button>
          </div>
        </div>

        {menuOpen && (
          <div id="mobile-nav" className="animate-fade-in border-t border-border lg:hidden">
            <nav aria-label={t("nav.main", "Main")} className="mx-auto grid max-w-6xl gap-1 p-3">
              {NAV.map(({ to, labelKey, fallback, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-3 text-base font-medium",
                      isActive ? "bg-brand-50 text-brand-700" : "text-fg hover:bg-surface-muted",
                    )
                  }
                >
                  <span className="flex size-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    <Icon className="size-4.5" />
                  </span>
                  {t(labelKey, fallback)}
                </NavLink>
              ))}
              <div className="mt-2 flex items-center justify-between gap-3 border-t border-border px-1 pt-3">
                <LanguageSwitch />
                {status === "authenticated" ? (
                  <Button asChild variant="secondary" size="sm">
                    <Link to="/account">
                      <UserRound aria-hidden="true" />
                      {t("account", "Account")}
                    </Link>
                  </Button>
                ) : (
                  <Button asChild size="sm">
                    <Link to="/login">{t("signIn", "Sign in")}</Link>
                  </Button>
                )}
              </div>
            </nav>
          </div>
        )}
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="relative mt-8 overflow-hidden bg-brand-950 text-white/75 dark:bg-surface">
        <div
          className="pointer-events-none absolute -right-32 -top-32 size-96 rounded-full bg-brand-500/25 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-40 -left-24 size-96 rounded-full bg-accent-500/10 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative mx-auto max-w-6xl px-4 pb-8 pt-14">
          <div className="grid gap-10 border-b border-white/10 pb-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
            <div className="max-w-xs">
              <Link to="/" className="inline-block rounded-lg [&_span]:text-white">
                <Logo label={t("brand", "Nirnoy Diagnostics")} />
              </Link>
              <p className="mt-4 text-sm leading-relaxed">
                {t(
                  "footer.tagline",
                  "Accurate lab diagnostics with home sample collection and QR-verified digital reports.",
                )}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white ring-1 ring-white/15">
                  <Award className="size-3.5 text-brand-300" />
                  ISO 15189
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white ring-1 ring-white/15">
                  <ShieldCheck className="size-3.5 text-brand-300" />
                  {t("footer.verified", "Verified reports")}
                </span>
              </div>
            </div>
            <FooterColumn title={t("footer.explore", "Explore")}>
              <FooterLink to="/tests">{t("nav.tests", "All Tests")}</FooterLink>
              <FooterLink to="/packages">{t("nav.packages", "Health Packages")}</FooterLink>
              <FooterLink to="/concerns">{t("nav.concerns", "Health Concerns")}</FooterLink>
              <FooterLink to="/centres">{t("nav.centres", "Branch Locator")}</FooterLink>
            </FooterColumn>
            <FooterColumn title={t("footer.services", "Services")}>
              <FooterLink to="/book">{t("footer.homeCollection", "Home Sample Collection")}</FooterLink>
              <FooterLink to="/account/bookings">{t("footer.trackBooking", "Track Booking")}</FooterLink>
              <FooterLink to="/account">{t("footer.reports", "Online Reports")}</FooterLink>
            </FooterColumn>
            <FooterColumn title={t("footer.help", "Support")}>
              <li className="flex items-center gap-2">
                <Phone className="size-4 text-brand-300" /> Hotline: 16XXX
              </li>
              <li className="flex items-center gap-2">
                <Mail className="size-4 text-brand-300" /> support@nirnoy.com
              </li>
              <li className="flex items-center gap-2">
                <MapPin className="size-4 text-brand-300" /> Dhaka, Bangladesh
              </li>
            </FooterColumn>
          </div>
          <div className="flex flex-col gap-4 pt-6 text-sm sm:flex-row sm:items-center sm:justify-between">
            <p>
              © {new Date().getFullYear()} {t("brand", "Nirnoy Diagnostics")}. All rights reserved.
            </p>
            <LanguageSwitch className="self-start border-white/15 bg-white/5 [&_button:not([aria-pressed=true])]:text-white/70 [&_button:not([aria-pressed=true]):hover]:bg-white/10 [&_button:not([aria-pressed=true]):hover]:text-white" />
          </div>
        </div>
      </footer>
      <ScrollRestoration />
    </div>
  );
}

function FooterColumn({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-4 font-display text-sm font-bold uppercase tracking-wider text-white">{title}</p>
      <ul className="space-y-2.5 text-sm">{children}</ul>
    </div>
  );
}

function FooterLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <li>
      <Link
        to={to}
        className="group inline-flex items-center gap-1 rounded hover:text-white"
      >
        <span className="link-underline">{children}</span>
        <ArrowRight className="size-3.5 -translate-x-1 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
      </Link>
    </li>
  );
}
