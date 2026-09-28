import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../cn";

/**
 * Surface container. Every card responds to hover with a soft shadow; `interactive`
 * adds a lift + brand-tinted border for tiles that are clickable as a whole.
 */
export function Card({
  className,
  interactive = false,
  ...props
}: HTMLAttributes<HTMLDivElement> & { interactive?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border border-border bg-surface shadow-[var(--shadow-card)] transition-[box-shadow,border-color,transform] duration-200 hover:shadow-[var(--shadow-hover)] dark:shadow-none",
        interactive && "hover-lift",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({
  title,
  description,
  action,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4 p-5 pb-0 sm:p-6 sm:pb-0", className)}>
      <div className="min-w-0">
        <h2 className="text-lg font-bold text-fg">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 sm:p-6", className)} {...props} />;
}

const alertVariants = cva(
  "flex animate-fade-in gap-3 rounded-[var(--radius-md)] border border-l-4 p-3.5 text-sm",
  {
  variants: {
    tone: {
      info: "border-info/25 border-l-info bg-info-bg text-fg [&>svg]:text-info",
      success: "border-success/25 border-l-success bg-success-bg text-fg [&>svg]:text-success",
      warning: "border-warning/25 border-l-warning bg-warning-bg text-fg [&>svg]:text-warning",
      danger: "border-danger/25 border-l-danger bg-danger-bg text-fg [&>svg]:text-danger",
    },
  },
  defaultVariants: { tone: "info" },
  },
);

const ALERT_ICONS = { info: Info, success: CheckCircle2, warning: TriangleAlert, danger: AlertCircle };

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: VariantProps<typeof alertVariants> & {
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  const Icon = ALERT_ICONS[tone ?? "info"];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(alertVariants({ tone }), className)}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && "mt-0.5 text-muted")}>{children}</div>}
      </div>
    </div>
  );
}

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset transition-colors",
  {
    variants: {
      tone: {
        neutral: "bg-surface-muted text-fg ring-border",
        brand: "bg-brand-50 text-brand-700 ring-brand-600/15",
        success: "bg-success-bg text-success ring-success/20",
        warning: "bg-warning-bg text-warning ring-warning/20",
        danger: "bg-danger-bg text-danger ring-danger/20",
        accent: "bg-accent-50 text-accent-600 ring-accent-500/20",
        info: "bg-info-bg text-info ring-info/20",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({
  tone,
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-shimmer rounded-[var(--radius-sm)] bg-[linear-gradient(90deg,var(--surface-muted)_25%,var(--border)_50%,var(--surface-muted)_75%)] bg-[length:200%_100%]",
        className,
      )}
      {...props}
    />
  );
}

export function Spinner({ label, className }: { label: string; className?: string }) {
  return (
    <span role="status" className={cn("inline-flex items-center gap-2 text-sm text-muted", className)}>
      <span className="relative size-5" aria-hidden="true">
        <span className="absolute inset-0 rounded-full border-2 border-brand-100" />
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-brand-600 border-r-brand-400" />
      </span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
