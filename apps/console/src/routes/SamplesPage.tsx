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
  AlertTriangle,
  Barcode,
  CheckCircle2,
  History,
  QrCode,
  RefreshCw,
  Search,
  Truck,
} from "lucide-react";
import { useState } from "react";

export default function SamplesPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [barcodeInput, setBarcodeInput] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"accession" | "transfers">("accession");
  const [scannedSample, setScannedSample] = useState<any | null>(null);
  const [rejectModalSample, setRejectModalSample] = useState<any | null>(null);
  const [selectedReasonId, setSelectedReasonId] = useState<string>("");
  const [rejectNotes, setRejectNotes] = useState<string>("");
  const [isSuccessFeedback, setIsSuccessFeedback] = useState<string | null>(null);

  // Rejection reasons query
  const { data: rejectionReasons } = useQuery({
    queryKey: ["sample-rejection-reasons"],
    queryFn: () => unwrap(api.GET("/api/v1/samples/rejection-reasons")),
  });

  // Transfers query
  const {
    data: transfers,
    isLoading: transfersLoading,
    refetch: refetchTransfers,
  } = useQuery({
    queryKey: ["sample-transfers"],
    queryFn: () => unwrap(api.GET("/api/v1/samples/transfers")),
  });

  const scanBarcodeMutation = useMutation({
    mutationFn: async (barcode: string) => {
      return unwrap(
        api.GET("/api/v1/samples/barcode/{barcode}", {
          params: {
            path: { barcode },
          },
        }),
      );
    },
    onSuccess: (data) => {
      setScannedSample(data);
      setIsSuccessFeedback(null);
    },
  });

  const receiveSampleMutation = useMutation({
    mutationFn: async (barcodes: string[]) => {
      const labId = scannedSample?.lab_id || "00000000-0000-0000-0000-000000000001";
      return unwrap(
        api.POST("/api/v1/samples/receive", {
          body: {
            barcodes,
            lab_id: labId,
          },
        }),
      );
    },
    onSuccess: () => {
      setIsSuccessFeedback("Sample successfully accessioned and marked RECEIVED at laboratory.");
      if (scannedSample) {
        setScannedSample({ ...scannedSample, status: "RECEIVED" });
      }
      queryClient.invalidateQueries({ queryKey: ["sample-transfers"] });
    },
  });

  const rejectSampleMutation = useMutation({
    mutationFn: async ({
      sampleId,
      reasonId,
      notes,
    }: {
      sampleId: string;
      reasonId: string;
      notes?: string;
    }) => {
      return unwrap(
        api.POST("/api/v1/samples/{sample_id}/reject", {
          params: {
            path: { sample_id: sampleId },
          },
          body: {
            rejection_reason_id: reasonId,
            notes,
            trigger_recollection: true,
          },
        }),
      );
    },
    onSuccess: () => {
      setRejectModalSample(null);
      setScannedSample(null);
      setSelectedReasonId("");
      setRejectNotes("");
      setIsSuccessFeedback("Sample marked REJECTED and automated recollection triggered.");
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CREATED":
        return <Badge tone="neutral">Label Created</Badge>;
      case "COLLECTED":
        return <Badge tone="brand">Collected</Badge>;
      case "IN_TRANSIT":
        return <Badge tone="neutral">In Transit</Badge>;
      case "RECEIVED":
        return <Badge tone="success">Received at Lab</Badge>;
      case "REJECTED":
        return <Badge tone="danger">Rejected</Badge>;
      default:
        return <Badge tone="neutral">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Sample Logistics & Accessioning
          </h1>
          <p className="text-sm text-muted">
            Track specimen chain of custody, perform batch manifests, and manage lab accession.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex rounded-lg border border-border bg-surface p-1">
          <button
            type="button"
            className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              activeTab === "accession"
                ? "bg-brand-50 text-brand-700"
                : "text-muted hover:text-foreground"
            }`}
            onClick={() => setActiveTab("accession")}
          >
            <Barcode className="size-3.5" />
            Barcode Accessioning
          </button>
          <button
            type="button"
            className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              activeTab === "transfers"
                ? "bg-brand-50 text-brand-700"
                : "text-muted hover:text-foreground"
            }`}
            onClick={() => setActiveTab("transfers")}
          >
            <Truck className="size-3.5" />
            Transfer Manifests
          </button>
        </div>
      </div>

      {isSuccessFeedback && (
        <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success-bg p-4 text-sm text-success">
          <CheckCircle2 className="size-4 shrink-0 text-success" />
          <span>{isSuccessFeedback}</span>
        </div>
      )}

      {activeTab === "accession" ? (
        <div className="space-y-6">
          {/* Scanner / Barcode Input Card */}
          <Card>
            <CardBody className="space-y-4">
              <h2 className="text-sm font-semibold text-foreground">Scan or Enter Specimen Barcode</h2>
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-72 flex-1">
                  <QrCode className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
                  <Input
                    placeholder="Scan tube barcode (e.g. SMP-2026-000001)..."
                    value={barcodeInput}
                    onChange={(e) => setBarcodeInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && barcodeInput.trim()) {
                        scanBarcodeMutation.mutate(barcodeInput.trim());
                      }
                    }}
                    className="pl-9 font-mono font-medium"
                  />
                </div>
                <Button
                  variant="primary"
                  onClick={() => {
                    if (barcodeInput.trim()) {
                      scanBarcodeMutation.mutate(barcodeInput.trim());
                    }
                  }}
                  disabled={scanBarcodeMutation.isPending || !barcodeInput.trim()}
                >
                  <Search className="size-4 mr-1" />
                  {scanBarcodeMutation.isPending ? "Searching..." : "Lookup Barcode"}
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Sample Result / Details */}
          {scannedSample && (
            <Card>
              <CardBody className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                      <Barcode className="size-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-base font-bold text-foreground">
                          {scannedSample.barcode}
                        </span>
                        {getStatusBadge(scannedSample.status)}
                      </div>
                      <p className="text-xs text-muted">
                        Container: {scannedSample.container} · Booking ID: {scannedSample.booking_id}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {scannedSample.status !== "RECEIVED" && scannedSample.status !== "REJECTED" && (
                      <Button
                        variant="primary"
                        onClick={() => receiveSampleMutation.mutate([scannedSample.barcode])}
                        disabled={receiveSampleMutation.isPending}
                      >
                        <CheckCircle2 className="size-4 mr-1" />
                        {receiveSampleMutation.isPending ? "Accessioning..." : "Accession / Mark Received"}
                      </Button>
                    )}
                    {scannedSample.status !== "REJECTED" && (
                      <Button
                        variant="secondary"
                        className="text-danger hover:border-danger/40 hover:bg-danger-bg hover:text-danger"
                        onClick={() => setRejectModalSample(scannedSample)}
                      >
                        <AlertTriangle className="size-4 mr-1 text-danger" />
                        Reject Sample
                      </Button>
                    )}
                  </div>
                </div>

                {/* Chain of custody audit trail */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    <History className="size-4 text-muted" />
                    <span>Chain of Custody Events</span>
                  </div>

                  <div className="relative border-l border-border pl-4 space-y-4 text-xs">
                    {(scannedSample.events || []).map((ev: any) => (
                      <div key={ev.id} className="relative">
                        <div className="absolute -left-[21px] top-1 size-2.5 rounded-full bg-brand-600 ring-4 ring-surface" />
                        <div className="font-semibold text-foreground">{ev.event_type}</div>
                        <div className="text-muted">
                          {new Date(ev.created_at).toLocaleString()} · Location: {ev.location_type}
                        </div>
                        {ev.notes && <div className="mt-0.5 text-foreground italic">{ev.notes}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              </CardBody>
            </Card>
          )}
        </div>
      ) : (
        /* Transfer Manifests View */
        <Card>
          <CardBody className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                Batch Transfer Manifests (Centre → Lab)
              </h2>
              <Button variant="secondary" size="sm" onClick={() => void refetchTransfers()}>
                <RefreshCw className="size-3.5 mr-1" />
                Refresh
              </Button>
            </div>

            {transfersLoading ? (
              <LoadingRows label="Loading transfer manifests..." />
            ) : (transfers || []).length === 0 ? (
              <div className="p-8 text-center text-muted">No batch transfer manifests found.</div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                    <tr>
                      <th className="px-4 py-3">Manifest Code</th>
                      <th className="px-4 py-3">Sample Count</th>
                      <th className="px-4 py-3">Temperature</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Dispatched At</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border bg-surface">
                    {(transfers || []).map((tr: any) => (
                      <tr key={tr.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                        <td className="px-4 py-3 font-mono font-semibold text-foreground">
                          {tr.manifest_code}
                        </td>
                        <td className="px-4 py-3 text-xs">{tr.sample_count} tubes</td>
                        <td className="px-4 py-3 text-xs">
                          {tr.temperature_celsius != null ? `${tr.temperature_celsius}°C` : "Ambient"}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={tr.status === "RECEIVED" ? "success" : "brand"}>
                            {tr.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-xs text-muted">
                          {new Date(tr.dispatched_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {tr.status !== "RECEIVED" ? (
                            <Button size="sm" variant="primary">
                              <CheckCircle2 className="size-3.5 mr-1" />
                              Receive Batch
                            </Button>
                          ) : (
                            <span className="text-xs text-muted">Received</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Rejection Reason Modal */}
      {rejectModalSample && (
        <Modal
          open={true}
          onOpenChange={() => setRejectModalSample(null)}
          title={`Reject Sample (${rejectModalSample.barcode})`}
          description="Select standard rejection reason. Automatic recollection will be booked for the patient."
          footer={
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setRejectModalSample(null)}
                disabled={rejectSampleMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  if (!selectedReasonId) return;
                  rejectSampleMutation.mutate({
                    sampleId: rejectModalSample.id,
                    reasonId: selectedReasonId,
                    notes: rejectNotes || undefined,
                  });
                }}
                disabled={rejectSampleMutation.isPending || !selectedReasonId}
              >
                {rejectSampleMutation.isPending ? "Rejecting..." : "Confirm Sample Rejection"}
              </Button>
            </div>
          }
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Rejection Reason Code</label>
              <Select
                value={selectedReasonId}
                onChange={(e) => setSelectedReasonId(e.target.value)}
              >
                <option value="">Select standard rejection reason...</option>
                {(rejectionReasons || []).map((r: any) => (
                  <option key={r.id} value={r.id}>
                    {r.name_en} ({r.code})
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Technician Notes</label>
              <Input
                placeholder="e.g. Severely hemolyzed blood sample, tube damaged in transit..."
                value={rejectNotes}
                onChange={(e) => setRejectNotes(e.target.value)}
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
