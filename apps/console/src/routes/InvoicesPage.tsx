import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Input,
  LoadingRows,
  Modal,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  FileText,
  Receipt,
  RefreshCw,
  Search,
} from "lucide-react";
import { useState } from "react";

export default function InvoicesPage() {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null);

  const {
    data: invoices,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["billing-invoices", typeFilter, statusFilter],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/billing/invoices", {
          params: {
            query: {
              bill_to_type: typeFilter || undefined,
              status: statusFilter || undefined,
            },
          },
        }),
      ),
  });

  const payMutation = useMutation({
    mutationFn: async (invoiceId: string) => {
      return unwrap(
        api.POST("/api/v1/billing/invoices/{invoice_id}/pay", {
          params: { path: { invoice_id: invoiceId } },
          body: { notes: "Settled via Console" },
        }),
      );
    },
    onSuccess: (data: any) => {
      toast.success(`Invoice ${data?.invoice_no || ""} marked as PAID.`);
      void queryClient.invalidateQueries({ queryKey: ["billing-invoices"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to mark invoice as paid");
    },
  });

  const formatBDT = (poisha: number) => {
    const taka = poisha / 100;
    return `৳${taka.toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PAID":
        return <Badge tone="success">Paid</Badge>;
      case "ISSUED":
        return <Badge tone="brand">Issued</Badge>;
      case "OVERDUE":
        return <Badge tone="danger">Overdue</Badge>;
      case "CANCELLED":
        return <Badge tone="neutral">Cancelled</Badge>;
      default:
        return <Badge tone="neutral">{status}</Badge>;
    }
  };

  const filteredInvoices = (invoices || []).filter((inv: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      inv.invoice_no?.toLowerCase().includes(q) ||
      inv.bill_to_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("billing.title")}</h1>
          <p className="text-sm text-muted">{t("billing.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={`size-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardBody className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by invoice number or recipient name..."
              className="pl-9"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">All Bill Types</option>
              <option value="PATIENT">Patient</option>
              <option value="CORPORATE">Corporate</option>
              <option value="PARTNER">Partner</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">All Statuses</option>
              <option value="ISSUED">Issued</option>
              <option value="PAID">Paid</option>
              <option value="OVERDUE">Overdue</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </CardBody>
      </Card>

      {/* Invoices List */}
      <Card>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-6">
              <LoadingRows rows={5} label="Loading invoices..." />
            </div>
          ) : !filteredInvoices?.length ? (
            <div className="p-8">
              <EmptyState
                icon={<Receipt className="size-8" />}
                title={t("billing.empty")}
                description="Institutional, corporate, and patient invoices will appear here."
              />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredInvoices.map((inv: any) => (
                <div
                  key={inv.id}
                  className="flex flex-col gap-4 p-5 transition-colors hover:bg-surface-muted sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-fg">{inv.invoice_no}</span>
                      {getStatusBadge(inv.status)}
                      <Badge tone="neutral">{inv.bill_to_type}</Badge>
                    </div>
                    <div className="text-sm font-medium text-fg">
                      Recipient: {inv.bill_to_name}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 text-xs text-muted">
                      <span>Issued: {new Date(inv.issued_at).toLocaleDateString()}</span>
                      <span>Due: {new Date(inv.due_date).toLocaleDateString()}</span>
                      <span>Items: {inv.items?.length || 0}</span>
                      {inv.paid_at && (
                        <span className="text-success">
                          Paid: {new Date(inv.paid_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center">
                    <div className="text-right">
                      <div className="text-lg font-bold text-fg">
                        {formatBDT(inv.total)}
                      </div>
                      <div className="text-xs text-muted">
                        Subtotal: {formatBDT(inv.subtotal)}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setSelectedInvoice(inv)}
                      >
                        <FileText className="size-3.5" />
                        Details
                      </Button>
                      {inv.status !== "PAID" && (
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={payMutation.isPending}
                          onClick={() => payMutation.mutate(inv.id)}
                        >
                          <CheckCircle className="size-3.5" />
                          Mark Paid
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Invoice Details Modal */}
      {selectedInvoice && (
        <Modal
          open={!!selectedInvoice}
          onOpenChange={(open) => !open && setSelectedInvoice(null)}
          title={`Invoice ${selectedInvoice.invoice_no}`}
        >
          <div className="space-y-4 py-2">
            <div className="flex justify-between border-b border-border pb-3">
              <div>
                <div className="text-xs text-muted">Billed To</div>
                <div className="font-semibold text-fg">{selectedInvoice.bill_to_name}</div>
                <div className="text-xs text-muted">Type: {selectedInvoice.bill_to_type}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted">Status</div>
                <div>{getStatusBadge(selectedInvoice.status)}</div>
                <div className="text-xs text-muted">
                  Due: {new Date(selectedInvoice.due_date).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted">
                Line Items
              </div>
              <div className="divide-y divide-border rounded-[var(--radius-md)] border border-border">
                {selectedInvoice.items?.map((item: any) => (
                  <div key={item.id} className="flex justify-between p-3 text-sm">
                    <div>
                      <div className="font-medium text-fg">{item.description}</div>
                      <div className="text-xs text-muted">
                        Qty: {item.quantity} × {formatBDT(item.unit_price)}
                      </div>
                    </div>
                    <div className="font-semibold text-fg">{formatBDT(item.total_amount)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-1 rounded-[var(--radius-md)] bg-surface-muted p-3 text-sm">
              <div className="flex justify-between text-muted">
                <span>Subtotal:</span>
                <span>{formatBDT(selectedInvoice.subtotal)}</span>
              </div>
              <div className="flex justify-between text-muted">
                <span>Discount:</span>
                <span>-{formatBDT(selectedInvoice.discount)}</span>
              </div>
              <div className="flex justify-between text-muted">
                <span>Tax (VAT):</span>
                <span>+{formatBDT(selectedInvoice.tax)}</span>
              </div>
              <div className="flex justify-between border-t border-border pt-1 font-bold text-fg">
                <span>Total:</span>
                <span>{formatBDT(selectedInvoice.total)}</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setSelectedInvoice(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
