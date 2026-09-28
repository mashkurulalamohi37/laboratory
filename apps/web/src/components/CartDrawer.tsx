import { useState } from "react";
import { useCart } from "@nirnoy/app-core";
import { Button, Drawer } from "@nirnoy/ui";
import { ArrowRight, Package, ShieldCheck, ShoppingBag, TestTube2, Trash2 } from "lucide-react";
import { Link } from "react-router";

export function CartDrawer() {
  const { items, itemCount, subtotal, removeItem } = useCart();
  const [open, setOpen] = useState(false);

  const formatTk = (poisha: number) => `৳${Math.round(poisha / 100).toLocaleString()}`;
  const mrpTotal = items.reduce((sum, item) => sum + (item.mrp ?? item.price), 0);
  const savings = Math.max(0, mrpTotal - subtotal);

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen(true)}
        className="group relative rounded-full"
        aria-label={itemCount > 0 ? `Shopping Cart (${itemCount})` : "Shopping Cart"}
      >
        <ShoppingBag className="size-5 transition-transform group-hover:-rotate-6 group-hover:scale-110" />
        {itemCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex size-5 animate-fade-in items-center justify-center rounded-full bg-accent-500 text-[11px] font-bold text-white ring-2 ring-surface">
            {itemCount}
          </span>
        )}
      </Button>

      <Drawer
        open={open}
        onOpenChange={setOpen}
        title="Your Selected Tests"
        description={itemCount > 0 ? `${itemCount} item${itemCount === 1 ? "" : "s"} in your cart` : undefined}
      >
        <div className="flex h-full flex-col justify-between">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="relative">
                <div className="absolute inset-0 scale-150 rounded-full bg-brand-100/60 blur-xl" aria-hidden="true" />
                <div className="relative flex size-20 items-center justify-center rounded-3xl bg-gradient-to-br from-brand-50 to-brand-100 text-brand-600">
                  <ShoppingBag className="size-9" />
                </div>
              </div>
              <p className="mt-6 text-lg font-bold text-fg">Your cart is empty</p>
              <p className="mt-1 max-w-xs text-sm text-muted">
                Add tests or health packages to start booking.
              </p>
              <Button asChild className="mt-6" onClick={() => setOpen(false)}>
                <Link to="/tests">
                  Browse Tests
                  <ArrowRight className="transition-transform group-hover/btn:translate-x-1" />
                </Link>
              </Button>
            </div>
          ) : (
            <>
              <ul className="flex flex-1 flex-col gap-2.5 overflow-y-auto">
                {items.map((item) => {
                  const Icon = item.type === "PACKAGE" ? Package : TestTube2;
                  return (
                    <li
                      key={item.id}
                      className="group flex animate-fade-in items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface p-3 transition-all hover:border-brand-300 hover:shadow-[var(--shadow-card)]"
                    >
                      <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition-transform group-hover:scale-105">
                        <Icon className="size-5" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-fg">{item.name}</p>
                        <p className="mt-0.5 flex items-baseline gap-2 text-sm tabular-nums">
                          <span className="font-bold text-brand-700">{formatTk(item.price)}</span>
                          {item.mrp && item.mrp > item.price && (
                            <s className="text-xs text-muted">{formatTk(item.mrp)}</s>
                          )}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeItem(item.id)}
                        className="flex size-9 items-center justify-center rounded-lg text-muted opacity-70 hover:bg-danger-bg hover:text-danger hover:opacity-100"
                        aria-label={`Remove ${item.name}`}
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </li>
                  );
                })}
              </ul>

              <div className="mt-6 space-y-3 rounded-[var(--radius-lg)] bg-surface-muted/70 p-4">
                {savings > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">You save</span>
                    <span className="font-semibold text-success">−{formatTk(savings)}</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-muted">Total Amount</span>
                  <span className="font-display text-2xl font-extrabold text-fg">{formatTk(subtotal)}</span>
                </div>

                <Button asChild size="lg" className="w-full" onClick={() => setOpen(false)}>
                  <Link to="/book">
                    Proceed to Schedule
                    <ArrowRight className="transition-transform group-hover/btn:translate-x-1" />
                  </Link>
                </Button>
                <p className="flex items-center justify-center gap-1.5 text-xs text-muted">
                  <ShieldCheck className="size-3.5 text-success" />
                  Secure booking · Verified digital reports
                </p>
              </div>
            </>
          )}
        </div>
      </Drawer>
    </>
  );
}
