import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "../cn";

export const buttonVariants = cva(
  "group/btn relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] font-semibold transition-all duration-200 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.97] disabled:pointer-events-none disabled:opacity-55 [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:transition-transform",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-brand text-white shadow-[var(--shadow-brand)] hover:-translate-y-px hover:brightness-110 hover:shadow-[0_10px_28px_-8px_color-mix(in_srgb,var(--brand-600)_70%,transparent)] dark:text-bg",
        secondary:
          "border border-border bg-surface text-fg shadow-[var(--shadow-card)] hover:-translate-y-px hover:border-brand-300 hover:bg-brand-50/60 hover:text-brand-700 hover:shadow-[var(--shadow-hover)]",
        outline:
          "border border-brand-600/40 bg-transparent text-brand-700 hover:border-brand-600 hover:bg-brand-50",
        soft: "bg-brand-50 text-brand-700 hover:bg-brand-100",
        ghost: "text-fg hover:bg-surface-muted hover:text-brand-700",
        danger:
          "bg-danger text-white shadow-[0_6px_18px_-6px_color-mix(in_srgb,var(--danger)_60%,transparent)] hover:-translate-y-px hover:brightness-110",
        link: "h-auto px-0 text-brand-600 underline-offset-4 hover:text-brand-700 hover:underline active:scale-100",
      },
      size: {
        sm: "h-9 px-3.5 text-sm",
        md: "h-11 px-5 text-sm sm:h-10",
        lg: "h-12 px-7 text-base",
        icon: "size-10",
      },
      block: { true: "w-full" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, block, asChild, loading, disabled, children, type, ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      type={asChild ? undefined : (type ?? "button")}
      className={cn(buttonVariants({ variant, size, block }), className)}
      disabled={asChild ? undefined : disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {loading && <Loader2 className="animate-spin" aria-hidden="true" />}
          {children}
        </>
      )}
    </Comp>
  );
});
