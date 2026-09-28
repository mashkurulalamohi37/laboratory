import { Loader2, Search, X } from "lucide-react";
import { useId, useMemo, useState, type KeyboardEvent } from "react";

import { cn } from "../cn";

export interface SearchSuggestion {
  key: string;
  group: string;
  label: string;
  detail?: string;
}

/**
 * Search field with grouped autocomplete (WAI-ARIA combobox + listbox). Arrow keys move
 * through suggestions, Enter opens the active one or submits the query, Escape closes the
 * list (and clears the field when it is already closed).
 */
export function SearchBox({
  value,
  onValueChange,
  suggestions,
  groupLabels,
  onSelect,
  onSubmit,
  label,
  placeholder,
  submitLabel,
  clearLabel,
  emptyText,
  loading = false,
  size = "md",
  className,
}: {
  value: string;
  onValueChange: (value: string) => void;
  suggestions: SearchSuggestion[];
  groupLabels: Record<string, string>;
  onSelect: (suggestion: SearchSuggestion) => void;
  onSubmit: (query: string) => void;
  label: string;
  placeholder?: string;
  submitLabel: string;
  clearLabel: string;
  emptyText: string;
  loading?: boolean;
  size?: "md" | "lg";
  className?: string;
}) {
  const id = useId();
  const listId = `${id}-list`;
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const groups = useMemo(() => {
    const order: string[] = [];
    const byGroup: Record<string, SearchSuggestion[]> = {};
    for (const s of suggestions) {
      if (!byGroup[s.group]) {
        byGroup[s.group] = [];
        order.push(s.group);
      }
      byGroup[s.group]!.push(s);
    }
    return order.map((g) => ({ group: g, items: byGroup[g]! }));
  }, [suggestions]);
  const flat = groups.flatMap((g) => g.items);
  const showList = open && value.trim().length >= 2;
  const optionId = (index: number) => `${id}-opt-${index}`;

  const choose = (s: SearchSuggestion) => {
    setOpen(false);
    setActive(-1);
    onSelect(s);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      const last = flat.length - 1;
      if (last >= 0) {
        setActive((i) =>
          e.key === "ArrowDown" ? (i >= last ? 0 : i + 1) : i <= 0 ? last : i - 1,
        );
      }
    } else if (e.key === "Enter" && showList && active >= 0 && flat[active]) {
      e.preventDefault();
      choose(flat[active]!);
    } else if (e.key === "Escape") {
      if (showList) setOpen(false);
      else onValueChange("");
      setActive(-1);
    }
  };

  let index = -1;
  return (
    <form
      role="search"
      className={cn("relative", className)}
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) {
          setOpen(false);
          onSubmit(value.trim());
        }
      }}
    >
      <label htmlFor={`${id}-input`} className="sr-only">
        {label}
      </label>
      <div
        className={cn(
          "group/search flex items-center gap-2 rounded-full border border-border bg-surface pl-5 pr-1.5 shadow-[var(--shadow-hover)] transition-[border-color,box-shadow] duration-200 hover:border-brand-300 focus-within:border-brand-500 focus-within:shadow-[0_0_0_5px_color-mix(in_srgb,var(--brand-500)_15%,transparent),var(--shadow-hover)]",
          size === "lg" ? "h-14" : "h-11",
        )}
      >
        <Search className="size-5 shrink-0 text-muted transition-colors group-focus-within/search:text-brand-600" aria-hidden="true" />
        <input
          id={`${id}-input`}
          type="search"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && active >= 0 ? optionId(active) : undefined}
          autoComplete="off"
          enterKeyHint="search"
          value={value}
          placeholder={placeholder}
          onChange={(e) => {
            onValueChange(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
          className="h-full min-w-0 flex-1 bg-transparent text-base text-fg outline-none placeholder:text-muted/80 [&::-webkit-search-cancel-button]:hidden"
        />
        {loading && <Loader2 className="size-4 shrink-0 animate-spin text-muted" aria-hidden="true" />}
        {value && (
          <button
            type="button"
            aria-label={clearLabel}
            className="flex size-9 shrink-0 items-center justify-center rounded-full text-muted hover:bg-surface-muted hover:text-fg"
            onClick={() => onValueChange("")}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        )}
        <button
          type="submit"
          className={cn(
            "shrink-0 rounded-full bg-gradient-brand px-5 font-semibold text-white shadow-[var(--shadow-brand)] transition-all hover:brightness-110 active:scale-95 dark:text-bg",
            size === "lg" ? "h-11 px-6" : "h-8 text-sm",
          )}
        >
          {submitLabel}
        </button>
      </div>

      <div
        id={listId}
        role="listbox"
        aria-label={label}
        hidden={!showList}
        className="absolute inset-x-0 top-full z-40 mt-2 max-h-[70vh] animate-fade-in overflow-y-auto rounded-[var(--radius-lg)] border border-border bg-surface p-2 text-left shadow-[var(--shadow-pop)]"
      >
        {showList && flat.length === 0 && !loading && (
          <p className="px-3 py-2 text-sm text-muted">{emptyText}</p>
        )}
        {groups.map(({ group, items }) => (
          <div key={group} role="group" aria-label={groupLabels[group] ?? group} className="py-1">
            <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-muted" aria-hidden="true">
              {groupLabels[group] ?? group}
            </p>
            {items.map((s) => {
              index += 1;
              const i = index;
              return (
                <div
                  key={s.key}
                  id={optionId(i)}
                  role="option"
                  aria-selected={i === active}
                  tabIndex={-1}
                  onMouseDown={(e) => e.preventDefault()} // keep focus in the input
                  onMouseEnter={() => setActive(i)}
                  onClick={() => choose(s)}
                  className={cn(
                    "flex cursor-pointer items-baseline justify-between gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm transition-colors",
                    i === active ? "bg-brand-50 font-medium text-brand-700" : "text-fg",
                  )}
                >
                  <span className="min-w-0 truncate">{s.label}</span>
                  {s.detail && <span className="shrink-0 tabular-nums text-muted">{s.detail}</span>}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </form>
  );
}
