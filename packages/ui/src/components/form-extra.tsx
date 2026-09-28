import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { cn } from "../cn";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, rows = 4, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        rows={rows}
        className={cn(
          "w-full rounded-[var(--radius-md)] border border-border bg-surface px-3.5 py-2.5 text-base text-fg shadow-[var(--shadow-card)] placeholder:text-muted/70 transition-[border-color,box-shadow] duration-200 hover:border-border-strong focus-visible:border-brand-500 focus-visible:shadow-[0_0_0_4px_color-mix(in_srgb,var(--brand-500)_18%,transparent)] focus-visible:outline-none disabled:opacity-60 aria-[invalid=true]:border-danger sm:text-sm",
          className,
        )}
        {...props}
      />
    );
  },
);

/** Native checkbox with a visible label (the whole row is clickable). */
export const Checkbox = forwardRef<
  HTMLInputElement,
  Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: React.ReactNode; hint?: string }
>(function Checkbox({ label, hint, className, id, ...props }, ref) {
  return (
    <label
      className={cn(
        "-mx-2 flex cursor-pointer items-start gap-3 rounded-[var(--radius-sm)] px-2 py-1.5 text-sm transition-colors hover:bg-surface-muted",
        className,
      )}
      htmlFor={id}
    >
      <input
        ref={ref}
        id={id}
        type="checkbox"
        className="mt-0.5 size-4 shrink-0 cursor-pointer rounded border-border accent-[var(--brand-600)]"
        {...props}
      />
      <span className="min-w-0">
        <span className="text-fg">{label}</span>
        {hint && <span className="block text-muted">{hint}</span>}
      </span>
    </label>
  );
});
