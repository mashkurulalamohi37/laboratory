import { Eye, EyeOff } from "lucide-react";
import { forwardRef, useState, type InputHTMLAttributes, type SelectHTMLAttributes } from "react";

import { cn } from "../cn";

const fieldBase =
  "w-full rounded-[var(--radius-md)] border border-border bg-surface px-3.5 text-base text-fg shadow-[var(--shadow-card)] placeholder:text-muted/70 transition-[border-color,box-shadow,background-color] duration-200 hover:border-border-strong focus-visible:border-brand-500 focus-visible:shadow-[0_0_0_4px_color-mix(in_srgb,var(--brand-500)_18%,transparent)] focus-visible:outline-none disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-60 aria-[invalid=true]:border-danger aria-[invalid=true]:focus-visible:shadow-[0_0_0_4px_color-mix(in_srgb,var(--danger)_18%,transparent)] sm:text-sm";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props },
  ref,
) {
  return <input ref={ref} className={cn(fieldBase, "h-11 sm:h-10", className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select ref={ref} className={cn(fieldBase, "h-11 cursor-pointer pr-8 sm:h-10", className)} {...props}>
        {children}
      </select>
    );
  },
);

/** Bangladesh mobile input: phone keypad, tel autocomplete. Accepts 01…, 8801…, +8801…. */
export const PhoneInput = forwardRef<HTMLInputElement, InputProps>(function PhoneInput(
  { className, ...props },
  ref,
) {
  return (
    <Input
      ref={ref}
      type="tel"
      inputMode="tel"
      autoComplete="tel"
      placeholder="01XXX-XXXXXX"
      className={cn("tabular-nums", className)}
      {...props}
    />
  );
});

/**
 * One-time code: a single field (works with SMS autofill and screen readers, unlike
 * split digit boxes). Non-digits are stripped as the user types.
 */
export const OtpInput = forwardRef<HTMLInputElement, InputProps & { length?: number }>(
  function OtpInput({ className, length = 6, onChange, ...props }, ref) {
    return (
      <Input
        ref={ref}
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern={`\\d{${length}}`}
        maxLength={length}
        className={cn("text-center font-mono text-xl tracking-[0.5em] tabular-nums", className)}
        onChange={(e) => {
          e.target.value = e.target.value.replace(/\D/g, "").slice(0, length);
          onChange?.(e);
        }}
        {...props}
      />
    );
  },
);

export const PasswordInput = forwardRef<HTMLInputElement, InputProps & { toggleLabel?: string }>(
  function PasswordInput({ className, toggleLabel = "Show password", ...props }, ref) {
    const [visible, setVisible] = useState(false);
    return (
      <div className="relative">
        <Input
          ref={ref}
          type={visible ? "text" : "password"}
          className={cn("pr-11", className)}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute inset-y-1 right-1 flex w-9 items-center justify-center rounded-[var(--radius-sm)] text-muted hover:bg-surface-muted hover:text-brand-700"
          aria-label={toggleLabel}
          aria-pressed={visible}
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    );
  },
);
