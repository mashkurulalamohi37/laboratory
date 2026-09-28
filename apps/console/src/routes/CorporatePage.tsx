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
  Building2,
  Calendar,
  Plus,
  RefreshCw,
  Search,
  Upload,
  Users,
} from "lucide-react";
import { useState } from "react";

export default function CorporatePage() {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [rosterModalOpen, setRosterModalOpen] = useState(false);
  const [selectedCorporate, setSelectedCorporate] = useState<any | null>(null);

  // Form states for creating corporate client
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [creditLimit, setCreditLimit] = useState(500000);
  const [paymentTermsDays, setPaymentTermsDays] = useState(30);
  const [discountPct, setDiscountPct] = useState(15.0);

  // Form states for roster upload
  const [rosterText, setRosterText] = useState(
    "EMP-101, Rahim Chowdhury, +8801712345601, rahim@company.com, Software Engineer\n" +
      "EMP-102, Nusrat Jahan, +8801812345602, nusrat@company.com, HR Manager\n" +
      "EMP-103, Tanvir Hasan, +8801912345603, tanvir@company.com, Financial Analyst",
  );

  const {
    data: clients,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["corporate-clients"],
    queryFn: () => unwrap(api.GET("/api/v1/corporate/clients")),
  });

  const { data: employees, refetch: refetchEmployees } = useQuery({
    queryKey: ["corporate-employees", selectedCorporate?.id],
    queryFn: () => {
      if (!selectedCorporate?.id) return [];
      return unwrap(
        api.GET("/api/v1/corporate/clients/{corporate_id}/employees", {
          params: { path: { corporate_id: selectedCorporate.id } },
        }),
      );
    },
    enabled: !!selectedCorporate?.id,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      return unwrap(
        api.POST("/api/v1/corporate/clients", {
          body: {
            name,
            contact_person: contactPerson,
            contact_email: email || "billing@corporate.com",
            contact_phone: phone,
            credit_limit: creditLimit * 100, // convert BDT to poisha
            credit_days: paymentTermsDays,
          },
        }),
      );
    },
    onSuccess: (data: any) => {
      toast.success(`Corporate account "${data?.name}" registered successfully!`);
      setCreateModalOpen(false);
      setName("");
      setCode("");
      setContactPerson("");
      setPhone("");
      setEmail("");
      void queryClient.invalidateQueries({ queryKey: ["corporate-clients"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create corporate client");
    },
  });

  const uploadRosterMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCorporate?.id) throw new Error("No client selected");
      const lines = rosterText
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean);
      const employeesPayload = lines.map((line) => {
        const [empCode, empName, empPhone, empEmail, empDesig] = line.split(",").map((s) => s.trim());
        return {
          employee_code: empCode || "EMP-000",
          full_name: empName || "Employee",
          phone: empPhone || "+8801700000000",
          email: empEmail || null,
          designation: empDesig || "Staff",
        };
      });

      return unwrap(
        api.POST("/api/v1/corporate/clients/{corporate_id}/employees/upload", {
          params: { path: { corporate_id: selectedCorporate.id } },
          body: {
            employees: employeesPayload,
          },
        }),
      );
    },
    onSuccess: (res: any) => {
      toast.success(
        `Roster synced: ${res?.total_synced || 0} employees updated (${res?.valid_employees || 0} active).`,
      );
      setRosterModalOpen(false);
      void refetchEmployees();
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to upload roster");
    },
  });

  const monthlyBillingMutation = useMutation({
    mutationFn: async (corporateId: string) => {
      return unwrap(
        api.POST("/api/v1/corporate/clients/{corporate_id}/invoices/monthly", {
          params: { path: { corporate_id: corporateId } },
          body: {
            billing_month: new Date().toISOString().slice(0, 7),
            due_days: 30,
          },
        }),
      );
    },
    onSuccess: (inv: any) => {
      toast.success(`Consolidated invoice ${inv?.invoice_no} generated successfully!`);
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to run monthly billing");
    },
  });

  const filteredClients = (clients || []).filter((c: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return c.name?.toLowerCase().includes(q) || c.code?.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("corporate.title")}</h1>
          <p className="text-sm text-muted">{t("corporate.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={`size-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="primary" onClick={() => setCreateModalOpen(true)}>
            <Plus className="size-4" />
            {t("corporate.addClient")}
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
              placeholder="Search corporate client name or contract code..."
              className="pl-9"
            />
          </div>
        </CardBody>
      </Card>

      {/* Client List */}
      <Card>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-6">
              <LoadingRows rows={5} label="Loading corporate clients..." />
            </div>
          ) : !filteredClients?.length ? (
            <div className="p-8">
              <EmptyState
                icon={<Building2 className="size-8" />}
                title={t("corporate.empty")}
                description="B2B corporate clients with customized discount schedules and roster agreements will appear here."
              />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredClients.map((client: any) => (
                <div
                  key={client.id}
                  className="flex flex-col gap-4 p-5 transition-colors hover:bg-surface-muted sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-fg">{client.name}</span>
                      <Badge tone="brand">{client.code}</Badge>
                      <Badge tone={client.status === "ACTIVE" ? "success" : "neutral"}>
                        {client.status}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted">
                      Contact: {client.contact_person} | {client.phone} {client.email && `| ${client.email}`}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 text-xs text-muted">
                      <span>Discount: <strong>{client.discount_pct}%</strong></span>
                      <span>Payment Terms: <strong>{client.payment_terms_days} days</strong></span>
                      <span>Credit Limit: ৳{(client.credit_limit / 100).toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedCorporate(client);
                        setRosterModalOpen(true);
                      }}
                    >
                      <Users className="size-3.5" />
                      Roster
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={monthlyBillingMutation.isPending}
                      onClick={() => monthlyBillingMutation.mutate(client.id)}
                    >
                      <Calendar className="size-3.5" />
                      Run Monthly Billing
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Add Corporate Client Modal */}
      <Modal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="Register B2B Corporate Client"
      >
        <div className="space-y-4 py-2">
          <Field label="Company / Organization Name" required>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Grameenphone Ltd."
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Contract Code" required>
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. GP-CORP"
              />
            </Field>

            <Field label="Discount Percentage (%)" required>
              <Input
                type="number"
                value={discountPct}
                onChange={(e) => setDiscountPct(parseFloat(e.target.value) || 0)}
              />
            </Field>
          </div>

          <Field label="Contact Person" required>
            <Input
              value={contactPerson}
              onChange={(e) => setContactPerson(e.target.value)}
              placeholder="e.g. Head of HR & Health Benefits"
            />
          </Field>

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
                placeholder="corp-billing@company.com"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Credit Limit (BDT)">
              <Input
                type="number"
                value={creditLimit}
                onChange={(e) => setCreditLimit(parseInt(e.target.value) || 0)}
              />
            </Field>

            <Field label="Payment Terms (Days)">
              <Input
                type="number"
                value={paymentTermsDays}
                onChange={(e) => setPaymentTermsDays(parseInt(e.target.value) || 30)}
              />
            </Field>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!name || !code || !contactPerson || !phone || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Registering..." : "Save Corporate Client"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Roster Modal */}
      {selectedCorporate && (
        <Modal
          open={rosterModalOpen}
          onOpenChange={setRosterModalOpen}
          title={`Employee Roster — ${selectedCorporate.name}`}
        >
          <div className="space-y-4 py-2">
            <p className="text-xs text-muted">
              Add or sync eligible employees (CSV format: Employee ID, Full Name, Phone, Email, Designation).
            </p>

            <Field label="Roster CSV Data" required>
              <textarea
                value={rosterText}
                onChange={(e) => setRosterText(e.target.value)}
                rows={5}
                className="w-full font-mono text-xs rounded-[var(--radius-md)] border border-border bg-surface p-3 text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </Field>

            <div className="flex justify-between items-center pt-2">
              <span className="text-xs text-muted">
                {employees?.length || 0} active employees registered
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setRosterModalOpen(false)}>
                  Close
                </Button>
                <Button
                  variant="primary"
                  disabled={uploadRosterMutation.isPending}
                  onClick={() => uploadRosterMutation.mutate()}
                >
                  <Upload className="size-3.5" />
                  {uploadRosterMutation.isPending ? "Syncing..." : "Sync Roster"}
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
