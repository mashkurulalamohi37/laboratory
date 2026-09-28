import { ChevronRight } from "lucide-react";
import { Fragment, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "../cn";

export interface TabItem {
  id: string;
  label: ReactNode;
  content: ReactNode;
}

/**
 * Accessible tabs (WAI-ARIA tabs pattern): arrow keys / Home / End move between tabs,
 * only the active tab is in the tab order. Controlled via `value` + `onValueChange`.
 */
export function Tabs({
  items,
  value,
  onValueChange,
  label,
  className,
}: {
  items: TabItem[];
  value: string;
  onValueChange: (id: string) => void;
  label: string;
  className?: string;
}) {
  const base = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const focus = (index: number) => {
    const item = items[(index + items.length) % items.length];
    if (item) {
      onValueChange(item.id);
      refs.current[item.id]?.focus();
    }
  };
  const onKeyDown = (e: KeyboardEvent, index: number) => {
    const moves: Record<string, number> = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: items.length - 1,
    };
    const next = moves[e.key];
    if (next !== undefined) {
      e.preventDefault();
      focus(next);
    }
  };
  return (
    <div className={className}>
      <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-border [scrollbar-width:none]">
        {items.map((item, index) => {
          const selected = item.id === value;
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[item.id] = el;
              }}
              type="button"
              role="tab"
              id={`${base}-tab-${item.id}`}
              aria-selected={selected}
              aria-controls={`${base}-panel-${item.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onValueChange(item.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
              className={cn(
                "relative -mb-px whitespace-nowrap rounded-t-[var(--radius-sm)] px-4 py-2.5 text-sm font-semibold transition-colors after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:transition-all after:duration-300",
                selected
                  ? "text-brand-700 after:bg-brand-600"
                  : "text-muted after:scale-x-0 after:bg-brand-300 hover:bg-surface-muted/70 hover:text-fg hover:after:scale-x-100",
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {items.map((item) => (
        <div
          key={item.id}
          role="tabpanel"
          id={`${base}-panel-${item.id}`}
          aria-labelledby={`${base}-tab-${item.id}`}
          hidden={item.id !== value}
          tabIndex={0}
          className="animate-fade-in pt-4 focus-visible:outline-none"
        >
          {item.id === value && item.content}
        </div>
      ))}
    </div>
  );
}

export interface Crumb {
  label: ReactNode;
  /** Rendered with `renderLink` when set; the last crumb is the current page. */
  href?: string;
}

export function Breadcrumbs({
  items,
  label,
  renderLink,
  className,
}: {
  items: Crumb[];
  label: string;
  renderLink: (href: string, children: ReactNode) => ReactNode;
  className?: string;
}) {
  return (
    <nav
      aria-label={label}
      className={cn("text-sm text-muted [&_a]:rounded [&_a]:transition-colors [&_a:hover]:text-brand-700", className)}
    >
      <ol className="flex flex-wrap items-center gap-1">
        {items.map((crumb, i) => {
          const last = i === items.length - 1;
          return (
            <Fragment key={i}>
              <li className={cn("min-w-0", last && "truncate font-medium text-fg")} aria-current={last ? "page" : undefined}>
                {crumb.href && !last ? renderLink(crumb.href, crumb.label) : crumb.label}
              </li>
              {!last && (
                <li aria-hidden="true">
                  <ChevronRight className="size-3.5" />
                </li>
              )}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
