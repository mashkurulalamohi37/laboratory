import { CloudOff, Inbox, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../cn";
import { Button } from "./button";
import { Skeleton } from "./display";

/** Every data view renders one of: loading · empty · error · content. */

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex animate-fade-up flex-col items-center gap-4 px-6 py-14 text-center", className)}>
      <div className="relative">
        <div className="absolute inset-0 scale-150 rounded-full bg-brand-100/60 blur-xl" aria-hidden="true" />
        <div className="relative flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100 text-brand-600 ring-1 ring-brand-600/10 [&_svg]:size-7">
          {icon ?? <Inbox className="size-7" aria-hidden="true" />}
        </div>
      </div>
      <div>
        <p className="text-base font-semibold text-fg">{title}</p>
        {description && <p className="mt-1 max-w-sm text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title,
  description,
  requestId,
  onRetry,
  retryLabel = "Try again",
  referenceLabel = "Reference",
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  requestId?: string | null;
  onRetry?: () => void;
  retryLabel?: string;
  referenceLabel?: string;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn("flex animate-fade-up flex-col items-center gap-4 px-6 py-14 text-center", className)}
    >
      <div className="flex size-16 items-center justify-center rounded-2xl bg-danger-bg text-danger ring-1 ring-danger/15">
        <CloudOff className="size-7" aria-hidden="true" />
      </div>
      <div>
        <p className="text-base font-semibold text-fg">{title}</p>
        {description && <p className="mt-1 max-w-sm text-sm text-muted">{description}</p>}
        {requestId && (
          <p className="mt-3 inline-block rounded-md bg-surface-muted px-2 py-1 font-mono text-xs text-muted">
            {referenceLabel}: {requestId}
          </p>
        )}
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <RotateCw aria-hidden="true" />
          {retryLabel}
        </Button>
      )}
    </div>
  );
}

export function LoadingRows({ rows = 5, label }: { rows?: number; label: string }) {
  return (
    <div className="flex flex-col gap-3 p-4" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" style={{ opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}
