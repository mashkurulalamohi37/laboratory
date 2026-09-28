import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../cn";
import { Button } from "./button";
import { EmptyState, ErrorState, LoadingRows } from "./states";

export interface Column<T> {
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  className?: string;
  /** Hide below the `md` breakpoint (rows become cards on phones). */
  hideOnMobile?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string;
  caption: string;
  isLoading?: boolean;
  error?: { title: string; requestId?: string | null; onRetry?: () => void } | null;
  empty: { title: ReactNode; description?: ReactNode; action?: ReactNode };
  onRowClick?: (row: T) => void;
  loadingLabel?: string;
}

/**
 * Server-paginated data table with built-in loading / empty / error states. Rows are
 * keyboard-activatable when `onRowClick` is set. Below `md` it renders as stacked cards.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
  isLoading,
  error,
  empty,
  onRowClick,
  loadingLabel = "Loading",
}: DataTableProps<T>) {
  if (isLoading) return <LoadingRows label={loadingLabel} />;
  if (error) {
    return (
      <ErrorState title={error.title} requestId={error.requestId ?? null} onRetry={error.onRetry} />
    );
  }
  if (!rows || rows.length === 0) return <EmptyState {...empty} />;

  const interactive = Boolean(onRowClick);
  return (
    <>
      <table className="hidden w-full text-left text-sm md:table">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-border bg-surface-muted/60 text-xs uppercase tracking-wider text-muted">
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={cn("px-4 py-3 font-semibold", c.className)}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className={cn(
                "transition-colors duration-150 hover:bg-brand-50/40",
                interactive &&
                  "group/row cursor-pointer shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/70 hover:shadow-[inset_3px_0_0_var(--brand-500)] focus-visible:bg-brand-50/70 focus-visible:outline-offset-[-2px]",
              )}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRowClick(row);
                      }
                    }
                  : undefined
              }
              tabIndex={interactive ? 0 : undefined}
            >
              {columns.map((c) => (
                <td key={c.key} className={cn("px-4 py-3 align-middle", c.className)}>
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="divide-y divide-border md:hidden" aria-label={caption}>
        {rows.map((row) => {
          const content = (
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              {columns
                .filter((c) => !c.hideOnMobile)
                .map((c) => (
                  <div key={c.key} className="contents">
                    <dt className="text-muted">{c.header}</dt>
                    <dd className="min-w-0 break-words">{c.cell(row)}</dd>
                  </div>
                ))}
            </dl>
          );
          return (
            <li key={rowKey(row)}>
              {onRowClick ? (
                <button
                  type="button"
                  className="w-full p-4 text-left transition-colors hover:bg-brand-50/60 active:bg-brand-50"
                  onClick={() => onRowClick(row)}
                >
                  {content}
                </button>
              ) : (
                <div className="p-4">{content}</div>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  labels = { previous: "Previous", next: "Next", summary: (p, n) => `Page ${p} of ${n}` },
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  labels?: { previous: string; next: string; summary: (page: number, pages: number) => string };
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;
  return (
    <nav
      className="flex items-center justify-between gap-2 border-t border-border bg-surface-muted/40 px-4 py-3"
      aria-label="Pagination"
    >
      <p className="text-sm text-muted" aria-live="polite">
        {labels.summary(page, pages)}
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
          {labels.previous}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          {labels.next}
          <ChevronRight aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
