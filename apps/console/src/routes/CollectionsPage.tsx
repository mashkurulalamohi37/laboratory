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
  Calendar,
  CheckCircle2,
  MapPin,
  Navigation,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import { useState } from "react";

export default function CollectionsPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedAssignment, setSelectedAssignment] = useState<any | null>(null);
  const [verificationCodeInput, setVerificationCodeInput] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);

  const {
    data: assignments,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["collection-assignments", statusFilter],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/admin/collection/assignments", {
          params: {
            query: {
              status: statusFilter || undefined,
            },
          },
        }),
      ),
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({
      assignmentId,
      status,
      code,
      notes,
    }: {
      assignmentId: string;
      status: string;
      code?: string;
      notes?: string;
    }) => {
      return unwrap(
        api.POST("/api/v1/collection/assignments/{assignment_id}/status", {
          params: {
            path: { assignment_id: assignmentId },
          },
          body: {
            status,
            verification_code: code,
            notes,
            client_timestamp: new Date().toISOString(),
          },
        }),
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collection-assignments"] });
      setSelectedAssignment(null);
      setVerificationCodeInput("");
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.message || "Failed to update assignment status");
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ASSIGNED":
        return <Badge tone="brand">Assigned</Badge>;
      case "ACCEPTED":
        return <Badge tone="brand">Accepted</Badge>;
      case "ON_THE_WAY":
        return <Badge tone="neutral">On The Way</Badge>;
      case "ARRIVED":
        return <Badge tone="neutral">Arrived</Badge>;
      case "PATIENT_VERIFIED":
        return <Badge tone="success">Patient Verified</Badge>;
      case "COLLECTED":
        return <Badge tone="success">Collected</Badge>;
      case "CANCELLED":
        return <Badge tone="danger">Cancelled</Badge>;
      default:
        return <Badge tone="neutral">{status}</Badge>;
    }
  };

  const getNextAction = (status: string) => {
    switch (status) {
      case "PENDING":
      case "ASSIGNED":
        return { label: "Accept Trip", nextStatus: "ACCEPTED", icon: CheckCircle2 };
      case "ACCEPTED":
        return { label: "Start Trip (On The Way)", nextStatus: "ON_THE_WAY", icon: Navigation };
      case "ON_THE_WAY":
        return { label: "Mark Arrived", nextStatus: "ARRIVED", icon: MapPin };
      case "ARRIVED":
        return { label: "Verify Patient Code", nextStatus: "PATIENT_VERIFIED", icon: ShieldCheck, requiresCode: true };
      case "PATIENT_VERIFIED":
        return { label: "Complete Collection", nextStatus: "COLLECTED", icon: UserCheck };
      default:
        return null;
    }
  };

  const filtered = (assignments || []).filter((item: any) => {
    if (statusFilter && item.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchId = item.id.toLowerCase().includes(q);
      const matchBooking = item.booking_id.toLowerCase().includes(q);
      if (!matchId && !matchBooking) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Home Sample Collection Queue
          </h1>
          <p className="text-sm text-muted">
            Manage phlebotomist assignments, GPS dispatch, patient verification, and sample collection custody.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`size-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="relative min-w-64 flex-1">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Search assignment ID, booking ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="w-56">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="ASSIGNED">Assigned</option>
                <option value="ACCEPTED">Accepted</option>
                <option value="ON_THE_WAY">On The Way</option>
                <option value="ARRIVED">Arrived</option>
                <option value="PATIENT_VERIFIED">Patient Verified</option>
                <option value="COLLECTED">Collected</option>
                <option value="CANCELLED">Cancelled</option>
              </Select>
            </div>
          </div>

          {isLoading ? (
            <LoadingRows label="Loading assignments..." />
          ) : isError ? (
            <div className="p-8 text-center text-danger">Failed to load collection assignments.</div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-muted">No collection assignments found matching criteria.</div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">Assignment</th>
                    <th className="px-4 py-3">Scheduled Date</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Verification Code</th>
                    <th className="px-4 py-3">Timeline</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-surface">
                  {filtered.map((item: any) => {
                    const action = getNextAction(item.status);
                    const ActionIcon = action?.icon;
                    return (
                      <tr key={item.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                        <td className="px-4 py-3">
                          <div className="font-mono text-xs font-semibold text-foreground">
                            {item.id.slice(0, 8)}...
                          </div>
                          <div className="text-xs text-muted">
                            Booking: {item.booking_id.slice(0, 8)}...
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5 text-xs text-foreground">
                            <Calendar className="size-3.5 text-muted" />
                            {item.scheduled_date}
                          </div>
                        </td>
                        <td className="px-4 py-3">{getStatusBadge(item.status)}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1 rounded bg-brand-50 px-2 py-0.5 font-mono text-xs font-semibold text-brand-700">
                            {item.verification_code}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-xs text-muted space-y-0.5">
                            {item.accepted_at && <div>Accepted: {new Date(item.accepted_at).toLocaleTimeString()}</div>}
                            {item.arrived_at && <div>Arrived: {new Date(item.arrived_at).toLocaleTimeString()}</div>}
                            {item.collected_at && <div className="text-success font-medium">Collected: {new Date(item.collected_at).toLocaleTimeString()}</div>}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {action ? (
                            <Button
                              size="sm"
                              variant="primary"
                              onClick={() => {
                                setSelectedAssignment(item);
                                setActionError(null);
                              }}
                            >
                              {ActionIcon && <ActionIcon className="size-3.5 mr-1" />}
                              {action.label}
                            </Button>
                          ) : (
                            <span className="text-xs text-muted">Completed</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Action Advance Modal */}
      {selectedAssignment && (
        <Modal
          open={true}
          onOpenChange={() => setSelectedAssignment(null)}
          title="Update Collection Status"
          description={`Assignment: ${selectedAssignment.id.slice(0, 8)}... (Current: ${selectedAssignment.status})`}
          footer={
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setSelectedAssignment(null)}
                disabled={updateStatusMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  const action = getNextAction(selectedAssignment.status);
                  if (!action) return;
                  updateStatusMutation.mutate({
                    assignmentId: selectedAssignment.id,
                    status: action.nextStatus,
                    code: verificationCodeInput || undefined,
                  });
                }}
                disabled={updateStatusMutation.isPending}
              >
                {updateStatusMutation.isPending ? "Updating..." : "Confirm Transition"}
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

            {getNextAction(selectedAssignment.status)?.requiresCode && (
              <div className="space-y-2">
                <label className="text-xs font-medium text-foreground">
                  Enter 4-digit Patient Verification Code:
                </label>
                <Input
                  placeholder="e.g. 4821"
                  maxLength={6}
                  value={verificationCodeInput}
                  onChange={(e) => setVerificationCodeInput(e.target.value)}
                  className="font-mono text-center text-lg tracking-widest"
                />
                <p className="text-xs text-muted">
                  The patient received this verification code via SMS and on their booking confirmation.
                </p>
              </div>
            )}

            <p className="text-sm text-muted">
              Are you sure you want to advance this assignment to{" "}
              <strong className="text-foreground">
                {getNextAction(selectedAssignment.status)?.nextStatus}
              </strong>
              ?
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
