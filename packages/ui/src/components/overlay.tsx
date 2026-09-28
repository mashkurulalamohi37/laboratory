import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "./button";

const overlayClass =
  "fixed inset-0 z-40 bg-[color-mix(in_srgb,var(--brand-950)_45%,transparent)] backdrop-blur-sm data-[state=open]:animate-fade-in";

interface OverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  closeLabel?: string;
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  closeLabel = "Close",
}: OverlayProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlayClass} />
        <DialogPrimitive.Content
          className="fixed left-1/2 top-1/2 z-50 flex max-h-[90dvh] w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col rounded-[var(--radius-xl)] border border-border bg-surface shadow-[var(--shadow-pop)] data-[state=open]:animate-scale-in"
          aria-describedby={description ? undefined : ""}
        >
          <div className="flex items-start justify-between gap-4 p-6 pb-2">
            <div>
              <DialogPrimitive.Title className="text-lg font-bold">{title}</DialogPrimitive.Title>
              {description && (
                <DialogPrimitive.Description className="mt-1 text-sm text-muted">
                  {description}
                </DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" aria-label={closeLabel} className="shrink-0 rounded-full hover:rotate-90 hover:bg-surface-muted">
                <X />
              </Button>
            </DialogPrimitive.Close>
          </div>
          {children && <div className="overflow-y-auto px-6 py-2">{children}</div>}
          {footer && (
            <div className="mt-2 flex justify-end gap-2 rounded-b-[var(--radius-xl)] border-t border-border bg-surface-muted/50 px-6 py-4">
              {footer}
            </div>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/** Side sheet for create/edit forms and record details (full-width on phones). */
export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  closeLabel = "Close",
}: OverlayProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlayClass} />
        <DialogPrimitive.Content
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l border-border bg-surface shadow-[var(--shadow-pop)] data-[state=open]:animate-slide-in-right"
          aria-describedby={description ? undefined : ""}
        >
          <div className="flex items-start justify-between gap-4 border-b border-border bg-gradient-to-r from-brand-50/70 to-transparent p-5">
            <div className="min-w-0">
              <DialogPrimitive.Title className="text-lg font-bold">{title}</DialogPrimitive.Title>
              {description && (
                <DialogPrimitive.Description className="mt-1 text-sm text-muted">
                  {description}
                </DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" aria-label={closeLabel} className="shrink-0 rounded-full hover:rotate-90 hover:bg-surface-muted">
                <X />
              </Button>
            </DialogPrimitive.Close>
          </div>
          <div className="flex-1 overflow-y-auto p-5">{children}</div>
          {footer && (
            <div className="flex justify-end gap-2 border-t border-border bg-surface-muted/50 p-4">{footer}</div>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/**
 * Confirmation for consequential actions. With `confirmText`, the user must type it
 * (e.g. the account name) before a destructive action is enabled.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
  confirmText,
  typeToConfirmLabel,
  onConfirm,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  confirmText?: string;
  typeToConfirmLabel?: string;
  onConfirm: () => void;
  children?: ReactNode;
}) {
  const [typed, setTyped] = useState("");
  const blocked = confirmText !== undefined && typed.trim() !== confirmText;
  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) setTyped("");
        onOpenChange(next);
      }}
      title={title}
      description={description}
      closeLabel={cancelLabel}
      footer={
        <>
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? "danger" : "primary"}
            onClick={onConfirm}
            loading={loading}
            disabled={blocked}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {children}
        {confirmText !== undefined && (
          <label className="flex flex-col gap-1.5 text-sm">
            <span>{typeToConfirmLabel ?? `Type "${confirmText}" to confirm`}</span>
            <input
              className="h-10 rounded-[var(--radius-md)] border border-border bg-surface px-3 transition-colors hover:border-border-strong focus-visible:border-danger focus-visible:outline-none"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
            />
          </label>
        )}
      </div>
    </Modal>
  );
}
