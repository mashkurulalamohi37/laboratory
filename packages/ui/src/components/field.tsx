import * as LabelPrimitive from "@radix-ui/react-label";
import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";

import { cn } from "../cn";

interface FieldProps {
  label: ReactNode;
  hint?: ReactNode;
  error?: string | undefined;
  /** A single form control; `id`, `aria-invalid` and `aria-describedby` are injected. */
  children: ReactElement<Record<string, unknown>>;
  className?: string;
  required?: boolean;
}

/** Label + control + hint/error, wired together for assistive technology. */
export function Field({ label, hint, error, children, className, required }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  const control = isValidElement(children)
    ? cloneElement(children, {
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": describedBy,
        "aria-required": required || undefined,
      })
    : children;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <LabelPrimitive.Root htmlFor={id} className="text-sm font-medium text-fg">
        {label}
        {required && (
          <span className="text-danger" aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </LabelPrimitive.Root>
      {control}
      {error ? (
        <p id={errorId} className="animate-fade-in text-sm text-danger" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
