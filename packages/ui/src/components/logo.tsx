import { cn } from "../cn";

/**
 * Original placeholder mark: a droplet inside a magnifier ring ("diagnosis" = নির্ণয়).
 * Replace with the final brand asset once the name is confirmed.
 */
export function Logo({
  className,
  label = "Nirnoy Diagnostics",
  showWordmark = true,
}: {
  className?: string;
  label?: string;
  showWordmark?: boolean;
}) {
  return (
    <span className={cn("group/logo inline-flex items-center gap-2.5 font-semibold text-fg", className)}>
      <span className="relative flex size-9 shrink-0 items-center justify-center rounded-xl bg-gradient-brand shadow-[var(--shadow-brand)] transition-transform duration-300 group-hover/logo:-rotate-6 group-hover/logo:scale-105">
        <svg viewBox="0 0 32 32" className="size-6" aria-hidden="true">
          <circle cx="14" cy="14" r="9.5" fill="none" stroke="white" strokeWidth="3" />
          <path d="M21 21 27 27" stroke="white" strokeWidth="3.2" strokeLinecap="round" />
          <path d="M14 8.5c2.6 3.3 4 5.6 4 7.3a4 4 0 0 1-8 0c0-1.7 1.4-4 4-7.3Z" fill="var(--accent-400)" />
        </svg>
      </span>
      {showWordmark ? (
        <span className="font-display text-lg font-extrabold tracking-tight">{label}</span>
      ) : (
        <span className="sr-only">{label}</span>
      )}
    </span>
  );
}
