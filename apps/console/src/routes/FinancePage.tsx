import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import {
  Badge,
  Button,
  EmptyState,
  Input,
  LoadingRows,
  Modal,
  Select,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  CheckCircle2,
  FileSpreadsheet,
  Plus,
  Receipt,
  RefreshCw,
  Scale,
} from "lucide-react";
import { useState } from "react";

export default function FinancePage() {
  const { t } = useTranslation("console");
  const { api, can } = useAuth();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"reconciliation" | "expenses" | "arap">("reconciliation");
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().slice(0, 10)
  );

  // Expense Modal
  const [expenseModalOpen, setExpenseModalOpen] = useState(false);
  const [expenseCategory, setExpenseCategory] = useState("UTILITY");
  const [expenseAmountBdt, setExpenseAmountBdt] = useState("5000");
  const [expensePaidTo, setExpensePaidTo] = useState("");
  const [expensePaymentMethod, setExpensePaymentMethod] = useState("CASH");
  const [expenseNotes, setExpenseNotes] = useState("");

  // AR/AP Modal
  const [arapModalOpen, setArapModalOpen] = useState(false);
  const [arapType, setArapType] = useState<"RECEIVABLE" | "PAYABLE">("RECEIVABLE");
  const [arapPartyName, setArapPartyName] = useState("");
  const [arapAmountBdt, setArapAmountBdt] = useState("10000");
  const [arapDueDate, setArapDueDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [arapNotes, setArapNotes] = useState("");

  // Queries
  const { data: recon, isLoading: reconLoading, refetch: refetchRecon } = useQuery({
    queryKey: ["finance", "reconciliation", selectedDate],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/finance/reconciliation", {
          params: { query: { target_date: selectedDate } },
        })
      ),
  });

  const { data: expenses, isLoading: expensesLoading } = useQuery({
    queryKey: ["finance", "expenses"],
    queryFn: () => unwrap(api.GET("/api/v1/finance/expenses")),
  });

  const { data: arapRecords, isLoading: arapLoading } = useQuery({
    queryKey: ["finance", "arap"],
    queryFn: () => unwrap(api.GET("/api/v1/finance/ar-ap")),
  });

  // Mutations
  const createExpenseMutation = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/finance/expenses", {
          body: {
            category: expenseCategory,
            amount: Math.round(Number(expenseAmountBdt) * 100),
            paid_to: expensePaidTo,
            payment_method: expensePaymentMethod,
            expense_date: selectedDate,
            notes: expenseNotes || undefined,
          },
        })
      ),
    onSuccess: () => {
      setExpenseModalOpen(false);
      setExpensePaidTo("");
      setExpenseNotes("");
      void queryClient.invalidateQueries({ queryKey: ["finance"] });
    },
  });

  const createArapMutation = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/finance/ar-ap", {
          body: {
            record_type: arapType,
            party_name: arapPartyName,
            amount: Math.round(Number(arapAmountBdt) * 100),
            due_date: arapDueDate,
            notes: arapNotes || undefined,
          },
        })
      ),
    onSuccess: () => {
      setArapModalOpen(false);
      setArapPartyName("");
      setArapNotes("");
      void queryClient.invalidateQueries({ queryKey: ["finance", "arap"] });
    },
  });

  const formatBdt = (poisha: number) => {
    return `৳${(poisha / 100).toLocaleString("en-BD", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("finance.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("finance.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          {can("settings:manage") && (
            <>
              <Button variant="secondary" onClick={() => setArapModalOpen(true)}>
                <Scale className="size-4" />
                Add AR/AP Record
              </Button>
              <Button variant="primary" onClick={() => setExpenseModalOpen(true)}>
                <Plus className="size-4" />
                {t("finance.recordExpense")}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab("reconciliation")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
            activeTab === "reconciliation"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-muted hover:text-fg"
          }`}
        >
          <FileSpreadsheet className="size-4" />
          {t("finance.dailyRecon")}
        </button>
        <button
          onClick={() => setActiveTab("expenses")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
            activeTab === "expenses"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-muted hover:text-fg"
          }`}
        >
          <Receipt className="size-4" />
          Expense Vouchers ({expenses?.length ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("arap")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
            activeTab === "arap"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-muted hover:text-fg"
          }`}
        >
          <Scale className="size-4" />
          {t("finance.arAp")} ({arapRecords?.length ?? 0})
        </button>
      </div>

      {/* TAB 1: Daily Reconciliation */}
      {activeTab === "reconciliation" && (
        <div className="flex flex-col gap-6">
          {/* Date Picker Bar */}
          <div className="flex items-center justify-between rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center gap-3">
              <Calendar className="size-4 text-muted" />
              <label htmlFor="finance-reconciliation-date" className="text-xs font-medium text-muted">Reconciliation Date:</label>
              <input
                id="finance-reconciliation-date"
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-fg shadow-xs"
              />
            </div>
            <button
              onClick={() => void refetchRecon()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted hover:text-fg"
            >
              <RefreshCw className="size-3.5" />
              Recalculate
            </button>
          </div>

          {reconLoading ? (
            <LoadingRows rows={4} label="Calculating financial reconciliation audit..." />
          ) : (
            <>
              {/* Recon Cards */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted">
                    {t("finance.totalRevenue")}
                  </span>
                  <p className="mt-2 text-2xl font-bold text-fg">
                    {formatBdt(recon?.total_revenue ?? 0)}
                  </p>
                  <p className="mt-1 text-xs text-brand-600">Gross billed revenue</p>
                </div>

                <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted">
                    {t("finance.totalExpenses")}
                  </span>
                  <p className="mt-2 text-2xl font-bold text-amber-600">
                    {formatBdt(recon?.total_expenses ?? 0)}
                  </p>
                  <p className="mt-1 text-xs text-muted">Disbursed expenses</p>
                </div>

                <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted">
                    {t("finance.netCashFlow")}
                  </span>
                  <p
                    className={`mt-2 text-2xl font-bold ${
                      (recon?.net_operating_balance ?? 0) >= 0
                        ? "text-emerald-700"
                        : "text-red-700"
                    }`}
                  >
                    {formatBdt(recon?.net_operating_balance ?? 0)}
                  </p>
                  <p className="mt-1 text-xs text-muted">Revenue minus expenses</p>
                </div>

                <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted">
                    Pending Receivables
                  </span>
                  <p className="mt-2 text-2xl font-bold text-purple-700">
                    {formatBdt(recon?.receivables_pending ?? 0)}
                  </p>
                  <p className="mt-1 text-xs text-muted">Uncollected B2B & AR</p>
                </div>
              </div>

              {/* Status Banner */}
              <div
                className={`flex items-center justify-between rounded-xl border p-4 ${
                  (recon?.net_operating_balance ?? 0) >= 0
                    ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                    : "border-amber-200 bg-amber-50 text-amber-950"
                }`}
              >
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="size-5 text-emerald-600" />
                  <div>
                    <p className="text-sm font-semibold">
                      Audit Ledger for {selectedDate}
                    </p>
                    <p className="text-xs text-muted">
                      Diagnostic revenue ledger and expense vouchers consolidated for {selectedDate}.
                    </p>
                  </div>
                </div>
                <Badge tone={(recon?.net_operating_balance ?? 0) >= 0 ? "success" : "neutral"}>
                  {(recon?.net_operating_balance ?? 0) >= 0 ? "SURPLUS" : "DEFICIT"}
                </Badge>
              </div>
            </>
          )}
        </div>
      )}

      {/* TAB 2: Expense Vouchers */}
      {activeTab === "expenses" && (
        <div className="flex flex-col gap-4">
          {expensesLoading ? (
            <LoadingRows rows={5} label="Loading expense vouchers..." />
          ) : !expenses || expenses.length === 0 ? (
            <EmptyState
              icon={<Receipt className="size-8" />}
              title={t("finance.empty")}
              description="Record operational expense vouchers for center rent, utilities, consumables, and transport."
            />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">Voucher #</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Paid To</th>
                    <th className="px-4 py-3">Method</th>
                    <th className="px-4 py-3">Notes</th>
                    <th className="px-4 py-3 text-right">Amount (BDT)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {expenses.map((exp) => (
                    <tr key={exp.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                      <td className="px-4 py-3 font-mono font-medium text-fg">{exp.voucher_no}</td>
                      <td className="px-4 py-3">
                        <Badge tone="neutral">{exp.category}</Badge>
                      </td>
                      <td className="px-4 py-3 font-medium text-fg">{exp.paid_to}</td>
                      <td className="px-4 py-3 text-xs text-muted">{exp.payment_method}</td>
                      <td className="px-4 py-3 text-muted">{exp.notes || "—"}</td>
                      <td className="px-4 py-3 text-right font-semibold text-fg">
                        {formatBdt(exp.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AR/AP Ledger */}
      {activeTab === "arap" && (
        <div className="flex flex-col gap-4">
          {arapLoading ? (
            <LoadingRows rows={4} label="Loading AR/AP records..." />
          ) : !arapRecords || arapRecords.length === 0 ? (
            <EmptyState
              icon={<Scale className="size-8" />}
              title="No AR/AP Records"
              description="Track accounts receivable from corporate contracts and accounts payable to third-party diagnostic labs."
            />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Counterparty</th>
                    <th className="px-4 py-3">Due Date</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Amount (BDT)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {arapRecords.map((record) => {
                    const isRec = record.record_type === "RECEIVABLE";
                    return (
                      <tr key={record.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                        <td className="px-4 py-3">
                          <Badge tone={isRec ? "brand" : "neutral"}>
                            {record.record_type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 font-medium text-fg">
                          {record.party_name}
                        </td>
                        <td className="px-4 py-3 text-muted">
                          {record.due_date || "Open / Rolling"}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={record.status === "SETTLED" ? "success" : "neutral"}>
                            {record.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-fg">
                          {formatBdt(record.amount)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Record Expense Modal */}
      <Modal
        open={expenseModalOpen}
        onOpenChange={setExpenseModalOpen}
        title="Record Operating Expense Voucher"
      >
        <div className="flex flex-col gap-4 p-4">
          <div>
            <label htmlFor="finance-expense-category" className="text-xs font-medium text-muted">Category</label>
            <Select
              id="finance-expense-category"
              value={expenseCategory}
              onChange={(e) => setExpenseCategory(e.target.value)}
              className="mt-1"
            >
              <option value="SUPPLIES">Consumables & Supplies</option>
              <option value="UTILITY">Electricity & Utilities</option>
              <option value="LOGISTICS">Collector Transport & Logistics</option>
              <option value="RENT">Centre Space Lease / Rent</option>
              <option value="MAINTENANCE">Equipment Calibration & Servicing</option>
              <option value="SALARY">Staff Advance / Stipend</option>
              <option value="OTHER">Other Operating Expense</option>
            </Select>
          </div>

          <div>
            <label htmlFor="finance-expense-amount" className="text-xs font-medium text-muted">Amount in BDT (Taka)</label>
            <Input
              id="finance-expense-amount"
              type="number"
              value={expenseAmountBdt}
              onChange={(e) => setExpenseAmountBdt(e.target.value)}
              min={1}
              className="mt-1"
            />
          </div>

          <div>
            <label htmlFor="finance-expense-paid-to" className="text-xs font-medium text-muted">Paid To / Recipient</label>
            <Input
              id="finance-expense-paid-to"
              value={expensePaidTo}
              onChange={(e) => setExpensePaidTo(e.target.value)}
              placeholder="e.g. Popular Medical Supplies"
              className="mt-1"
            />
          </div>

          <div>
            <label htmlFor="finance-expense-notes" className="text-xs font-medium text-muted">Notes / Reason</label>
            <Input
              id="finance-expense-notes"
              value={expenseNotes}
              onChange={(e) => setExpenseNotes(e.target.value)}
              placeholder="e.g. Needles and vacutainer replenishment"
              className="mt-1"
            />
          </div>

          <div>
            <label htmlFor="finance-expense-payment-method" className="text-xs font-medium text-muted">Disbursement Method</label>
            <Select
              id="finance-expense-payment-method"
              value={expensePaymentMethod}
              onChange={(e) => setExpensePaymentMethod(e.target.value)}
              className="mt-1"
            >
              <option value="CASH">Cash (Petty Cash Vault)</option>
              <option value="BANK">Bank EFT / Real-Time NPSB</option>
              <option value="MFS">MFS (bKash / Nagad)</option>
            </Select>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setExpenseModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!expensePaidTo || Number(expenseAmountBdt) <= 0}
              onClick={() => createExpenseMutation.mutate()}
              loading={createExpenseMutation.isPending}
            >
              Disburse & Record
            </Button>
          </div>
        </div>
      </Modal>

      {/* AR/AP Record Modal */}
      <Modal
        open={arapModalOpen}
        onOpenChange={setArapModalOpen}
        title="Add AR / AP Ledger Entry"
      >
        <div className="flex flex-col gap-4 p-4">
          <div>
            <label htmlFor="finance-arap-type" className="text-xs font-medium text-muted">Type</label>
            <Select
              id="finance-arap-type"
              value={arapType}
              onChange={(e) => setArapType(e.target.value as any)}
              className="mt-1"
            >
              <option value="RECEIVABLE">Receivable (Incoming from B2B / Partner)</option>
              <option value="PAYABLE">Payable (Outgoing to Vendor / External Lab)</option>
            </Select>
          </div>

          <div>
            <label htmlFor="finance-arap-party-name" className="text-xs font-medium text-muted">Party Name</label>
            <Input
              id="finance-arap-party-name"
              value={arapPartyName}
              onChange={(e) => setArapPartyName(e.target.value)}
              placeholder="e.g. Grameenphone Healthcare Division"
              className="mt-1"
            />
          </div>

          <div>
            <label htmlFor="finance-arap-amount" className="text-xs font-medium text-muted">Amount in BDT (Taka)</label>
            <Input
              id="finance-arap-amount"
              type="number"
              value={arapAmountBdt}
              onChange={(e) => setArapAmountBdt(e.target.value)}
              min={1}
              className="mt-1"
            />
          </div>

          <div>
            <label htmlFor="finance-arap-due-date" className="text-xs font-medium text-muted">Settlement Due Date</label>
            <Input
              id="finance-arap-due-date"
              type="date"
              value={arapDueDate}
              onChange={(e) => setArapDueDate(e.target.value)}
              className="mt-1"
            />
          </div>

          <div>
            <label htmlFor="finance-arap-notes" className="text-xs font-medium text-muted">Notes</label>
            <Input
              id="finance-arap-notes"
              value={arapNotes}
              onChange={(e) => setArapNotes(e.target.value)}
              placeholder="Reference contract number or invoice reference"
              className="mt-1"
            />
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setArapModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!arapPartyName || Number(arapAmountBdt) <= 0}
              onClick={() => createArapMutation.mutate()}
              loading={createArapMutation.isPending}
            >
              Save Record
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
