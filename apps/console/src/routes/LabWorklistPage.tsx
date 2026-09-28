import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import {
  Badge,
  Button,
  Card,
  CardBody,
  Input,
  LoadingRows,
  Modal,
  Select,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  FileEdit,
  FlaskConical,
  Microscope,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

const DEPARTMENTS = [
  { value: "", label: "All Departments" },
  { value: "HEMATOLOGY", label: "Hematology" },
  { value: "BIOCHEMISTRY", label: "Biochemistry" },
  { value: "CLINICAL_PATHOLOGY", label: "Clinical Pathology" },
  { value: "MICROBIOLOGY", label: "Microbiology" },
  { value: "IMMUNOLOGY", label: "Immunology" },
  { value: "HISTOPATHOLOGY", label: "Histopathology" },
];

export default function LabWorklistPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [departmentFilter, setDepartmentFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Result Entry Modal State
  const [selectedOrderForEntry, setSelectedOrderForEntry] = useState<any | null>(null);
  const [parameterInputs, setParameterInputs] = useState<
    Array<{ parameter_id: string; parameter_name: string; value_numeric?: number; value_text?: string; unit?: string }>
  >([]);
  const [technicianNotes, setTechnicianNotes] = useState<string>("");

  // Verification Modal State
  const [selectedResultForVerification, setSelectedResultForVerification] = useState<any | null>(null);
  const [verificationNotes, setVerificationNotes] = useState<string>("");

  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const {
    data: labOrders,
    isLoading: isLoadingOrders,
    isError: isOrdersError,
    refetch: refetchOrders,
    isFetching: isFetchingOrders,
  } = useQuery({
    queryKey: ["lab-worklist-orders", departmentFilter, statusFilter, priorityFilter],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/lab/worklist", {
          params: {
            query: {
              status: statusFilter || undefined,
            },
          },
        }),
      ),
  });

  const { data: criticalAlerts, refetch: refetchAlerts } = useQuery({
    queryKey: ["lab-critical-alerts"],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/results/critical-alerts", {
          params: {
            query: {
              status: "TRIGGERED",
            },
          },
        }),
      ),
  });

  // Mutations
  const enterResultsMutation = useMutation({
    mutationFn: async ({
      orderItemId,
      parameters,
      notes,
    }: {
      orderItemId: string;
      parameters: typeof parameterInputs;
      notes?: string;
    }) => {
      return unwrap(
        api.POST("/api/v1/results/enter", {
          body: {
            lab_order_item_id: orderItemId,
            parameters: parameters.map((p) => ({
              parameter_id: p.parameter_id,
              value_numeric: p.value_numeric !== undefined && !isNaN(p.value_numeric) ? p.value_numeric : undefined,
              value_text: p.value_text || undefined,
            })),
            comments: notes ? [notes] : undefined,
          },
        }),
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-worklist-orders"] });
      queryClient.invalidateQueries({ queryKey: ["lab-critical-alerts"] });
      setSelectedOrderForEntry(null);
      setParameterInputs([]);
      setTechnicianNotes("");
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.message || "Failed to submit lab results");
    },
  });

  const verifyResultMutation = useMutation({
    mutationFn: async ({ resultId, notes }: { resultId: string; notes?: string }) => {
      return unwrap(
        api.POST("/api/v1/results/{result_id}/verify", {
          params: {
            path: { result_id: resultId },
          },
          body: {
            comments: notes,
          },
        }),
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-worklist-orders"] });
      queryClient.invalidateQueries({ queryKey: ["lab-critical-alerts"] });
      setSelectedResultForVerification(null);
      setVerificationNotes("");
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.message || "Failed to verify result. Note: Four-eyes rule prohibits self-verification.");
    },
  });

  const acknowledgeAlertMutation = useMutation({
    mutationFn: async ({ alertId }: { alertId: string }) => {
      return unwrap(
        api.POST("/api/v1/results/critical-alerts/{alert_id}/acknowledge", {
          params: {
            path: { alert_id: alertId },
          },
          body: {
            action_taken: "Acknowledged by laboratory team via admin console",
          },
        }),
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-critical-alerts"] });
    },
  });

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "STAT":
        return (
          <Badge tone="danger">
            <AlertOctagon className="size-3 mr-1 inline" /> STAT
          </Badge>
        );
      case "URGENT":
        return (
          <Badge tone="warning">
            <AlertTriangle className="size-3 mr-1 inline" /> URGENT
          </Badge>
        );
      default:
        return <Badge tone="neutral">ROUTINE</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PENDING":
        return <Badge tone="neutral">Pending</Badge>;
      case "IN_PROGRESS":
        return <Badge tone="brand">In Progress</Badge>;
      case "RESULTED":
        return <Badge tone="warning">Resulted (Pending Sign-off)</Badge>;
      case "VERIFIED":
        return <Badge tone="success">Verified & Released</Badge>;
      case "REJECTED":
        return <Badge tone="danger">Sample Rejected</Badge>;
      default:
        return <Badge tone="neutral">{status}</Badge>;
    }
  };

  const filteredOrders = (labOrders || []).filter((order: any) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchOrder = order.id?.toLowerCase().includes(q);
      const matchTest = order.test_name?.toLowerCase().includes(q);
      if (!matchOrder && !matchTest) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Laboratory Worklist & Diagnostics
          </h1>
          <p className="text-sm text-muted">
            Manage departmental queues, record parameter test results, and perform dual-signature verification.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void refetchOrders();
            void refetchAlerts();
          }}
          disabled={isFetchingOrders}
        >
          <RefreshCw className={`size-4 ${isFetchingOrders ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Critical Alerts Banner if any exist */}
      {criticalAlerts && criticalAlerts.length > 0 && (
        <div className="rounded-xl border border-danger/30 bg-danger-bg p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <ShieldAlert className="size-6 text-danger animate-bounce" />
            <div className="flex-1">
              <h3 className="text-sm font-bold text-danger">
                Action Required: {criticalAlerts.length} Unacknowledged Critical Value Alert(s)
              </h3>
              <p className="text-xs text-danger">
                Immediate clinical notification required. Please acknowledge receipt of the critical laboratory findings.
              </p>
            </div>
          </div>
          <div className="mt-3 divide-y divide-danger/30 rounded-lg border border-danger/30 bg-surface">
            {criticalAlerts.map((alert: any) => (
              <div key={alert.id} className="flex items-center justify-between p-3 text-xs">
                <div>
                  <span className="font-semibold text-danger">
                    Flag: {alert.flag} • Value: {alert.value_numeric ?? alert.value_text}
                  </span>
                  <span className="ml-2 text-muted">
                    Reported at {new Date(alert.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => acknowledgeAlertMutation.mutate({ alertId: alert.id })}
                  disabled={acknowledgeAlertMutation.isPending}
                >
                  <CheckCircle2 className="size-3.5 mr-1" /> Acknowledge Alert
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <Card>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="relative min-w-64 flex-1">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Search order item ID or test name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="w-52">
              <Select value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)}>
                {DEPARTMENTS.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-44">
              <Select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
                <option value="">All Priorities</option>
                <option value="STAT">STAT (Emergency)</option>
                <option value="URGENT">Urgent</option>
                <option value="ROUTINE">Routine</option>
              </Select>
            </div>
            <div className="w-44">
              <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">All Statuses</option>
                <option value="PENDING">Pending</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="RESULTED">Resulted</option>
                <option value="VERIFIED">Verified</option>
              </Select>
            </div>
          </div>

          {/* Worklist Table */}
          {isLoadingOrders ? (
            <LoadingRows label="Loading laboratory worklist..." />
          ) : isOrdersError ? (
            <div className="p-8 text-center text-danger">Failed to load lab worklist.</div>
          ) : filteredOrders.length === 0 ? (
            <div className="p-8 text-center text-muted">No laboratory orders found matching criteria.</div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">Item #</th>
                    <th className="px-4 py-3">Test</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-4 py-3">Sample Link</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-surface">
                  {filteredOrders.map((order: any) => (
                    <tr key={order.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                      <td className="px-4 py-3">
                        <div className="font-mono text-xs font-bold text-foreground">
                          {order.id.slice(0, 8)}...
                        </div>
                        <div className="text-xs text-muted">
                          Order: {order.lab_order_id.slice(0, 8)}...
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                          <Microscope className="size-3.5 text-muted" />
                          {order.test_name || "Diagnostic Test"}
                        </div>
                      </td>
                      <td className="px-4 py-3">{getPriorityBadge(order.priority || "ROUTINE")}</td>
                      <td className="px-4 py-3">
                        <div className="font-mono text-xs text-foreground">
                          {order.sample_id ? (
                            <span className="inline-flex items-center gap-1 rounded bg-surface-muted px-2 py-0.5">
                              <FlaskConical className="size-3 text-brand-600" />
                              {order.sample_id.slice(0, 8)}...
                            </span>
                          ) : (
                            <span className="text-muted italic">Pending Sample</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">{getStatusBadge(order.status)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {order.status === "PENDING" || order.status === "IN_PROGRESS" ? (
                            <Button
                              size="sm"
                              variant="primary"
                              onClick={() => {
                                setSelectedOrderForEntry(order);
                                setParameterInputs([
                                  {
                                    parameter_id: "00000000-0000-0000-0000-000000000001",
                                    parameter_name: "Hemoglobin / Analyte",
                                    value_numeric: undefined,
                                    unit: "g/dL",
                                  },
                                ]);
                                setActionError(null);
                              }}
                            >
                              <FileEdit className="size-3.5 mr-1" />
                              Enter Results
                            </Button>
                          ) : order.status === "RESULTED" ? (
                            <Button
                              size="sm"
                              variant="secondary"
                              className="border-brand-500 text-brand-700 hover:bg-brand-50"
                              onClick={() => {
                                setSelectedResultForVerification(order);
                                setActionError(null);
                              }}
                            >
                              <ShieldCheck className="size-3.5 mr-1 text-brand-600" />
                              Verify & Release
                            </Button>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-success font-medium">
                              <CheckCircle2 className="size-3.5" /> Released
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Modal: Enter Parameter Results */}
      {selectedOrderForEntry && (
        <Modal
          open={true}
          onOpenChange={() => setSelectedOrderForEntry(null)}
          title="Enter Lab Results"
          description={`Order Item #${selectedOrderForEntry.id.slice(0, 8)}...`}
          footer={
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setSelectedOrderForEntry(null)}
                disabled={enterResultsMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  enterResultsMutation.mutate({
                    orderItemId: selectedOrderForEntry.id,
                    parameters: parameterInputs,
                    notes: technicianNotes || undefined,
                  });
                }}
                disabled={enterResultsMutation.isPending}
              >
                {enterResultsMutation.isPending ? "Submitting..." : "Submit Results"}
              </Button>
            </div>
          }
        >
          <div className="space-y-4 py-2">
            {actionError && (
              <div className="rounded-md bg-danger-bg p-3 text-sm text-danger">
                {actionError}
              </div>
            )}

            <div className="rounded-lg border border-border bg-surface-muted/30 p-3 text-xs space-y-2">
              <div className="font-semibold text-foreground">Parameter Value Entry</div>
              <p className="text-muted">
                Values entered will be automatically evaluated against age- and sex-adjusted biological reference ranges.
              </p>

              {parameterInputs.map((param, idx) => (
                <div key={idx} className="flex items-center gap-3 bg-surface p-2.5 rounded-md border border-border">
                  <div className="flex-1 font-medium text-foreground text-xs">
                    {param.parameter_name}
                  </div>
                  <div className="w-36">
                    <Input
                      type="number"
                      step="any"
                      placeholder="Numeric Value"
                      value={param.value_numeric ?? ""}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        const updated = [...parameterInputs];
                        const target = updated[idx];
                        if (target) {
                          target.value_numeric = isNaN(val) ? undefined : val;
                          setParameterInputs(updated);
                        }
                      }}
                      className="text-xs"
                    />
                  </div>
                  <div className="w-16 text-xs text-muted font-mono">{param.unit}</div>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-foreground">Technician Observation Notes:</label>
              <Input
                placeholder="Optional internal remarks..."
                value={technicianNotes}
                onChange={(e) => setTechnicianNotes(e.target.value)}
                className="text-xs"
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Pathologist Verification */}
      {selectedResultForVerification && (
        <Modal
          open={true}
          onOpenChange={() => setSelectedResultForVerification(null)}
          title="Pathologist Sign-off & Verification"
          description={`Order Item #${selectedResultForVerification.id.slice(0, 8)}...`}
          footer={
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setSelectedResultForVerification(null)}
                disabled={verifyResultMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  verifyResultMutation.mutate({
                    resultId: selectedResultForVerification.id,
                    notes: verificationNotes || undefined,
                  });
                }}
                disabled={verifyResultMutation.isPending}
              >
                {verifyResultMutation.isPending ? "Verifying..." : "Verify & Authorize Release"}
              </Button>
            </div>
          }
        >
          <div className="space-y-4 py-2">
            {actionError && (
              <div className="rounded-md bg-danger-bg p-3 text-sm text-danger">
                {actionError}
              </div>
            )}

            <div className="rounded-lg border border-warning/30 bg-warning-bg p-3 text-xs text-warning">
              <div className="font-bold flex items-center gap-1.5">
                <ShieldAlert className="size-4 text-warning" />
                Mandatory Four-Eyes Rule
              </div>
              <p className="mt-1">
                In compliance with ISO 15189 and laboratory quality policies, the verifying pathologist must be a different authenticated user than the technician who entered the initial results.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-foreground">Pathologist Clinical Comments:</label>
              <Input
                placeholder="e.g. Verified findings; clinically correlated."
                value={verificationNotes}
                onChange={(e) => setVerificationNotes(e.target.value)}
                className="text-xs"
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
