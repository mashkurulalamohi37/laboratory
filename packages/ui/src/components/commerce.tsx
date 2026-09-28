import { cn } from "../cn";

/**
 * Price with optional struck-through MRP and a discount badge. Amounts arrive already
 * formatted (৳, digits per locale) so this component stays locale-agnostic.
 */
export function PriceTag({
  amount,
  mrp,
  off,
  mrpLabel,
  size = "md",
  className,
}: {
  amount: string;
  mrp?: string | null;
  off?: string | null;
  /** Accessible text for the MRP, e.g. "Regular price ৳500". */
  mrpLabel?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-baseline gap-x-2 gap-y-1 tabular-nums", className)}>
      <span
        className={cn(
          "font-display font-extrabold tracking-tight text-fg",
          size === "sm" && "text-base",
          size === "md" && "text-lg",
          size === "lg" && "text-2xl sm:text-3xl",
        )}
      >
        {amount}
      </span>
      {mrp && (
        <s className="text-sm text-muted" aria-label={mrpLabel}>
          {mrp}
        </s>
      )}
      {off && (
        <span className="rounded-full bg-accent-50 px-2 py-0.5 text-xs font-bold text-accent-600 ring-1 ring-inset ring-accent-500/20">
          {off}
        </span>
      )}
    </div>
  );
}
