import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Card, CardBody, CardHeader, cn, Skeleton } from "@nirnoy/ui";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  CalendarCheck,
  CheckCircle2,
  Clock,
  DollarSign,
  FileCheck2,
  FlaskConical,
  RefreshCw,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

const STAT_TONES = {
  brand: "bg-brand-50 text-brand-600 group-hover:bg-brand-600",
  info: "bg-info-bg text-info group-hover:bg-info",
  success: "bg-success-bg text-success group-hover:bg-success",
  warning: "bg-warning-bg text-warning group-hover:bg-warning",
} as const;

const STAT_BARS = {
  brand: "from-brand-400 to-brand-600",
  info: "from-blue-400 to-blue-600",
  success: "from-emerald-400 to-emerald-600",
  warning: "from-amber-300 to-amber-500",
} as const;

function StatCard({
  label,
  icon: Icon,
  tone,
  value,
  suffix,
  footer,
}: {
  label: string;
  icon: LucideIcon;
  tone: keyof typeof STAT_TONES;
  value: string;
  suffix?: string;
  footer?: ReactNode;
}) {
  return (
    <Card interactive className="group relative overflow-hidden p-5">
      <div
        className={cn(
          "absolute inset-x-0 top-0 h-1 bg-gradient-to-r opacity-0 transition-opacity duration-300 group-hover:opacity-100",
          STAT_BARS[tone],
        )}
        aria-hidden="true"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</span>
        <div
          className={cn(
            "rounded-xl p-2.5 transition-all duration-300 group-hover:scale-110 group-hover:text-white dark:group-hover:text-bg",
            STAT_TONES[tone],
          )}
        >
          <Icon className="size-4.5" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-display text-3xl font-extrabold tracking-tight text-fg tabular-nums">{value}</span>
        {suffix && <span className="text-xs text-muted">{suffix}</span>}
      </div>
      {footer && <div className="mt-3 border-t border-border pt-3 text-xs text-muted">{footer}</div>}
    </Card>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation("console");
  const { me, api } = useAuth();

  const { data: analytics, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["analytics", "dashboard"],
    queryFn: () => unwrap(api.GET("/api/v1/analytics/dashboard")),
    refetchInterval: 30000,
  });

  const { data: departments } = useQuery({
    queryKey: ["analytics", "departments"],
    queryFn: () => unwrap(api.GET("/api/v1/analytics/departments")),
  });

  const { data: tatData } = useQuery({
    queryKey: ["analytics", "tat"],
    queryFn: () => unwrap(api.GET("/api/v1/analytics/tat")),
  });

  if (!me) return null;

  const formatBdt = (poisha: number) => {
    const taka = poisha / 100;
    return `৳${taka.toLocaleString("en-BD", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Header */}
      <div className="relative overflow-hidden rounded-[var(--radius-xl)] bg-gradient-brand p-6 text-white shadow-[var(--shadow-pop)] sm:p-8">
        <div className="absolute -right-16 -top-16 size-64 rounded-full bg-white/10 blur-2xl" aria-hidden="true" />
        <div className="absolute -bottom-24 right-40 size-56 rounded-full bg-accent-500/25 blur-3xl" aria-hidden="true" />
        <div className="relative flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <p className="text-sm font-medium text-white/75">
              {new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}
            </p>
            <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">
              {t("dashboard.welcome", { name: me.full_name ?? me.phone ?? "" })}
            </h1>
            <p className="mt-1.5 flex items-center gap-2 text-sm text-white/80">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-white/70" />
                <span className="relative inline-flex size-2 rounded-full bg-white" />
              </span>
              {t("analytics.title")} · Live operations & diagnostic turnaround monitoring
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isRefetching}
            className="group inline-flex items-center gap-2 self-start rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white ring-1 ring-white/25 backdrop-blur hover:bg-white/25 active:scale-95 disabled:opacity-70 md:self-auto"
          >
            <RefreshCw className={`size-4 transition-transform duration-500 group-hover:rotate-180 ${isRefetching ? "animate-spin" : ""}`} />
            Refresh Live KPIs
          </button>
        </div>
      </div>

      {/* Critical Alert Warning Banner (if any) */}
      {analytics && analytics.critical_alerts_unack > 0 && (
        <div className="flex animate-fade-in flex-col justify-between gap-3 rounded-[var(--radius-lg)] border border-l-4 border-danger/30 border-l-danger bg-danger-bg p-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <div className="relative rounded-xl bg-danger p-2.5 text-white">
              <ShieldAlert className="size-5" />
              <span className="absolute -right-1 -top-1 size-3 animate-ping rounded-full bg-danger" />
            </div>
            <div>
              <p className="text-sm font-bold text-fg">
                Urgent Action Required: {analytics.critical_alerts_unack} Unacknowledged Critical Result Alert(s)
              </p>
              <p className="text-xs text-muted">
                Patients with severe abnormal laboratory values require immediate clinical notification and clinician sign-off.
              </p>
            </div>
          </div>
          <Badge tone="danger" className="self-start sm:self-auto">URGENT</Badge>
        </div>
      )}

      {/* KPI Cards Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" role="status" aria-label="Loading analytics KPIs...">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-36 rounded-[var(--radius-lg)]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label={t("analytics.todayBookings")}
            icon={CalendarCheck}
            tone="info"
            value={analytics?.today_bookings.toLocaleString() ?? "0"}
            suffix={`/ ${analytics?.total_bookings.toLocaleString() ?? 0} total`}
            footer={
              <span className="flex items-center gap-1 text-brand-600">
                <ArrowUpRight className="size-3.5" />
                Active booking velocity
              </span>
            }
          />
          <StatCard
            label={t("analytics.todayRevenue")}
            icon={DollarSign}
            tone="success"
            value={formatBdt(analytics?.today_revenue ?? 0)}
            footer={<span>Total gross: {formatBdt(analytics?.total_revenue ?? 0)}</span>}
          />
          <StatCard
            label={t("analytics.inLabSamples")}
            icon={FlaskConical}
            tone="warning"
            value={analytics?.samples_in_lab.toLocaleString() ?? "0"}
            suffix="samples"
            footer={
              <span className="flex items-center gap-1 text-success">
                <CheckCircle2 className="size-3.5" />
                {analytics?.results_verified ?? 0} results verified
              </span>
            }
          />
          <StatCard
            label={t("analytics.releasedReports")}
            icon={FileCheck2}
            tone="brand"
            value={analytics?.reports_released.toLocaleString() ?? "0"}
            suffix="signed"
            footer={<span>Pathologist certified & released</span>}
          />
        </div>
      )}

      {/* Operational Breakdown & TAT */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Departmental Workload */}
        <Card>
          <CardHeader
            title={t("analytics.deptWorkload")}
            action={<span className="flex size-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600"><Activity className="size-4" /></span>}
          />
          <CardBody>
            {departments && departments.length > 0 ? (
              <div className="space-y-4">
                {departments.map((dept) => {
                  const maxOrders = Math.max(
                    ...departments.map((d) => d.total_orders || 1),
                    1
                  );
                  const pct = Math.round((dept.total_orders / maxOrders) * 100);
                  return (
                    <div key={dept.department} className="group -mx-2 space-y-1.5 rounded-[var(--radius-sm)] px-2 py-1.5 transition-colors hover:bg-surface-muted/70">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-fg group-hover:text-brand-700">{dept.department}</span>
                        <span className="text-muted">
                          {dept.total_orders} total orders ({dept.completed_orders} completed)
                        </span>
                      </div>
                      <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-muted">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600 transition-all duration-700"
                          style={{ width: `${Math.max(pct, 5)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="rounded-[var(--radius-md)] border border-dashed border-border py-8 text-center text-sm text-muted">No department workload records yet.</p>
            )}
          </CardBody>
        </Card>

        {/* Turnaround Time (TAT) Benchmarks */}
        <Card>
          <CardHeader
            title={t("analytics.tatMetrics")}
            action={<span className="flex size-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600"><Clock className="size-4" /></span>}
          />
          <CardBody>
            {tatData ? (
              <div className="divide-y divide-border [&>div]:-mx-2 [&>div]:rounded-[var(--radius-sm)] [&>div]:px-2 [&>div]:transition-colors [&>div:hover]:bg-surface-muted/70">
                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-fg">Booking to Sample Collection</p>
                    <p className="text-xs text-muted">Phlebotomist dispatch & arrival latency</p>
                  </div>
                  <span className="text-sm font-semibold text-fg">
                    {tatData.avg_booking_to_collection_hours.toFixed(1)} hours
                  </span>
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-fg">Collection to Verification</p>
                    <p className="text-xs text-muted">Sample transit & laboratory analyzer run</p>
                  </div>
                  <span className="text-sm font-semibold text-fg">
                    {tatData.avg_collection_to_verify_hours.toFixed(1)} hours
                  </span>
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-fg">End-to-End Turnaround Time</p>
                    <p className="text-xs text-muted">
                      Total elapsed from order to final signed report ({tatData.total_samples_analyzed} samples)
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-brand-600">
                      {tatData.avg_overall_tat_hours.toFixed(1)} hours
                    </span>
                    <Badge tone="success">Active</Badge>
                  </div>
                </div>
              </div>
            ) : (
              <p className="rounded-[var(--radius-md)] border border-dashed border-border py-8 text-center text-sm text-muted">No turnaround time samples recorded yet.</p>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Staff Identity & Permissions */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("dashboard.rolesHeading")} />
          <CardBody className="flex flex-wrap gap-2">
            {me.roles.map((r) => (
              <Badge key={`${r.role}-${r.scope_type}-${r.scope_id ?? ""}`} tone="brand">
                {r.role.replaceAll("_", " ")}
                {r.scope_type !== "GLOBAL" && ` · ${r.scope_type}`}
              </Badge>
            ))}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title={t("dashboard.permissionsHeading")} />
          <CardBody>
            <ul className="flex flex-wrap gap-1.5">
              {me.permissions.map((p) => (
                <li key={p}>
                  <code className="rounded-md border border-border bg-surface-muted px-1.5 py-0.5 text-xs transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700">{p}</code>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
