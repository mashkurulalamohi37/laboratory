import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Field,
  Input,
  LoadingRows,
  Modal,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Network,
  Plus,
  RefreshCw,
  Search,
  Sliders,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";

export default function PartnerPage() {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [statementModalOpen, setStatementModalOpen] = useState(false);
  const [selectedPartner, setSelectedPartner] = useState<any | null>(null);

  // Form states for creating partner
  const [partnerType, setPartnerType] = useState("DOCTOR");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [payoutType, setPayoutType] = useState("MONTHLY");

  // Form states for commission rule
  const [ruleScope, setRuleScope] = useState("ALL");
  const [calculationType, setCalculationType] = useState("PERCENT");
  const [percentage, setPercentage] = useState(12.5);
  const [fixedAmount, setFixedAmount] = useState(100);

  const {
    data: partners,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["partners-network"],
    queryFn: () => unwrap(api.GET("/api/v1/partner/partners")),
  });

  const { data: statement, isLoading: statementLoading } = useQuery({
    queryKey: ["partner-statement", selectedPartner?.id],
    queryFn: () => {
      if (!selectedPartner?.id) return null;
      return unwrap(
        api.GET("/api/v1/partner/partners/{partner_id}/statement", {
          params: { path: { partner_id: selectedPartner.id } },
        }),
      );
    },
    enabled: !!selectedPartner?.id && statementModalOpen,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      return unwrap(
        api.POST("/api/v1/partner/partners", {
          body: {
            partner_type: partnerType,
            name,
            code,
            phone,
            email: email || undefined,
            commission_payout_type: payoutType,
          },
        }),
      );
    },
    onSuccess: (data: any) => {
      toast.success(`Partner ${data?.name} registered successfully!`);
      setCreateModalOpen(false);
      setName("");
      setCode("");
      setPhone("");
      setEmail("");
      void queryClient.invalidateQueries({ queryKey: ["partners-network"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to register partner");
    },
  });

  const ruleMutation = useMutation({
    mutationFn: async () => {
      if (!selectedPartner?.id) throw new Error("No partner selected");
      return unwrap(
        api.POST("/api/v1/partner/rules", {
          body: {
            partner_id: selectedPartner.id,
            scope: ruleScope,
            rule_type: calculationType,
            value: calculationType === "PERCENT" ? percentage : fixedAmount * 100,
            effective_from: new Date().toISOString().slice(0, 10),
          },
        }),
      );
    },
    onSuccess: () => {
      toast.success("Commission rule configured successfully!");
      setRuleModalOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["partners-network"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to add commission rule");
    },
  });

  const formatBDT = (poisha: number) => {
    return `৳${(poisha / 100).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const filteredPartners = (partners || []).filter((p: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return p.name?.toLowerCase().includes(q) || p.code?.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("partner.title")}</h1>
          <p className="text-sm text-muted">{t("partner.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={`size-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="primary" onClick={() => setCreateModalOpen(true)}>
            <Plus className="size-4" />
            {t("partner.addPartner")}
          </Button>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardBody className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search partner by name, ID code, or phone..."
              className="pl-9"
            />
          </div>
        </CardBody>
      </Card>

      {/* Partners List */}
      <Card>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-6">
              <LoadingRows rows={5} label="Loading partners..." />
            </div>
          ) : !filteredPartners?.length ? (
            <div className="p-8">
              <EmptyState
                icon={<Network className="size-8" />}
                title={t("partner.empty")}
                description="Healthcare clinics, referral doctors, and hospital partners will appear here."
              />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredPartners.map((partner: any) => (
                <div
                  key={partner.id}
                  className="flex flex-col gap-4 p-5 transition-colors hover:bg-surface-muted sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-fg">{partner.name}</span>
                      <Badge tone="brand">{partner.code}</Badge>
                      <Badge tone="neutral">{partner.partner_type}</Badge>
                      <Badge tone={partner.status === "ACTIVE" ? "success" : "neutral"}>
                        {partner.status}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted">
                      Phone: {partner.phone} {partner.email && `| ${partner.email}`}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 text-xs text-muted">
                      <span>Payout: <strong>{partner.commission_payout_type}</strong></span>
                      <span>Active Rules: {partner.rules?.length || 0}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedPartner(partner);
                        setRuleModalOpen(true);
                      }}
                    >
                      <Sliders className="size-3.5" />
                      Rules
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        setSelectedPartner(partner);
                        setStatementModalOpen(true);
                      }}
                    >
                      <TrendingUp className="size-3.5" />
                      Statement
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Register Partner Modal */}
      <Modal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="Register Healthcare Referral Partner"
      >
        <div className="space-y-4 py-2">
          <Field label="Partner Type" required>
            <select
              value={partnerType}
              onChange={(e) => setPartnerType(e.target.value)}
              className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="DOCTOR">Referring Doctor</option>
              <option value="CLINIC">Diagnostic Clinic</option>
              <option value="HOSPITAL">Hospital Partner</option>
              <option value="AGENT">Health Consultant / Agent</option>
            </select>
          </Field>

          <Field label="Full Name / Facility Name" required>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Dr. Shamsul Alam or Dhanmondi Care Clinic"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Partner Code" required>
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. PRT-DOC-102"
              />
            </Field>

            <Field label="Payout Schedule" required>
              <select
                value={payoutType}
                onChange={(e) => setPayoutType(e.target.value)}
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="MONTHLY">Monthly</option>
                <option value="BIWEEKLY">Bi-weekly</option>
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Phone" required>
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+8801700000000"
              />
            </Field>

            <Field label="Email">
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="doctor@hospital.org"
              />
            </Field>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!name || !code || !phone || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Registering..." : "Register Partner"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Add Commission Rule Modal */}
      {selectedPartner && (
        <Modal
          open={ruleModalOpen}
          onOpenChange={setRuleModalOpen}
          title={`Configure Commission Rule — ${selectedPartner.name}`}
        >
          <div className="space-y-4 py-2">
            <Field label="Rule Scope" required>
              <select
                value={ruleScope}
                onChange={(e) => setRuleScope(e.target.value)}
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="ALL">All Tests & Packages</option>
                <option value="CATEGORY">By Test Category</option>
                <option value="TEST">By Specific Test</option>
                <option value="PACKAGE">By Package</option>
              </select>
            </Field>

            <Field label="Calculation Mode" required>
              <select
                value={calculationType}
                onChange={(e) => setCalculationType(e.target.value)}
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="PERCENT">Percentage (%) of Gross Test Price</option>
                <option value="FIXED">Fixed Taka Amount per Referral</option>
              </select>
            </Field>

            {calculationType === "PERCENT" ? (
              <Field label="Commission Percentage (%)" required>
                <Input
                  type="number"
                  value={percentage}
                  onChange={(e) => setPercentage(parseFloat(e.target.value) || 0)}
                  placeholder="e.g. 15.0"
                />
              </Field>
            ) : (
              <Field label="Fixed Amount (BDT)" required>
                <Input
                  type="number"
                  value={fixedAmount}
                  onChange={(e) => setFixedAmount(parseFloat(e.target.value) || 0)}
                  placeholder="e.g. 200"
                />
              </Field>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setRuleModalOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={ruleMutation.isPending}
                onClick={() => ruleMutation.mutate()}
              >
                {ruleMutation.isPending ? "Saving..." : "Apply Rule"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Financial Statement Modal */}
      {selectedPartner && (
        <Modal
          open={statementModalOpen}
          onOpenChange={setStatementModalOpen}
          title={`Financial Statement — ${selectedPartner.name}`}
        >
          <div className="space-y-4 py-2">
            {statementLoading ? (
              <LoadingRows rows={4} label="Loading statement..." />
            ) : statement ? (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-[var(--radius-md)] bg-surface-muted p-3 text-center">
                    <div className="text-xs text-muted">Total Referrals</div>
                    <div className="text-xl font-bold text-fg">{statement.total_referrals}</div>
                  </div>
                  <div className="rounded-[var(--radius-md)] bg-surface-muted p-3 text-center">
                    <div className="text-xs text-muted">Gross Revenue</div>
                    <div className="text-xl font-bold text-fg">{formatBDT(statement.gross_revenue)}</div>
                  </div>
                  <div className="rounded-[var(--radius-md)] bg-brand-50 p-3 text-center">
                    <div className="text-xs text-brand-700">Earned Commission</div>
                    <div className="text-xl font-bold text-brand-900">{formatBDT(statement.earned_commission)}</div>
                  </div>
                  <div className="rounded-[var(--radius-md)] bg-success-bg p-3 text-center">
                    <div className="text-xs text-success">Pending Payout</div>
                    <div className="text-xl font-bold text-success">{formatBDT(statement.pending_commission)}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Referral Entries ({statement.entries?.length || 0})
                  </div>
                  {!statement.entries?.length ? (
                    <div className="p-4 text-center text-xs text-muted">
                      No referral ledger transactions recorded in this period.
                    </div>
                  ) : (
                    <div className="max-h-60 overflow-y-auto divide-y divide-border rounded-[var(--radius-md)] border border-border">
                      {statement.entries.map((entry: any) => (
                        <div key={entry.id} className="flex justify-between p-3 text-xs">
                          <div>
                            <div className="font-semibold text-fg">Ref #{entry.id.slice(0, 8)}</div>
                            <div className="text-muted">Gross: {formatBDT(entry.gross_amount)}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold text-brand-700">+{formatBDT(entry.commission_amount)}</div>
                            <Badge tone={entry.status === "PAID" ? "success" : "brand"}>{entry.status}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : null}

            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setStatementModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
