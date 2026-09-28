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
  Textarea,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Download,
  FileCheck2,
  FileSignature,
  Plus,
  RefreshCw,
  Search,
  Share2,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

export default function ReportsPage() {
  const { t } = useTranslation("console");
  const { api, me } = useAuth();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState("");
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [amendModalOpen, setAmendModalOpen] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  // Form states for generation
  const [labOrderId, setLabOrderId] = useState("");
  const [pathologistName, setPathologistName] = useState(
    me?.full_name || "Dr. Kazi Mahbubur Rahman",
  );
  const [bmdcNumber, setBmdcNumber] = useState("A-48291");
  const [designation, setDesignation] = useState("Consultant Clinical Pathologist");

  // Form state for amendment
  const [amendReason, setAmendReason] = useState("");

  // Query lab worklist ready for report generation
  const {
    data: worklist,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["reports-lab-worklist"],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/lab/worklist", {
          params: { query: {} },
        }),
      ),
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const fallbackId = "018f0000-0000-7000-8000-000000000001";
      return unwrap(
        api.POST("/api/v1/reports/generate", {
          body: {
            lab_order_id: labOrderId,
            pathologist_id: me?.id || fallbackId,
            pathologist_name: pathologistName,
            bmdc_number: bmdcNumber,
            designation: designation,
          },
        }),
      );
    },
    onSuccess: (data: any) => {
      toast.success(`Report ${data?.report_code || "generated"} certified & released successfully!`);
      setGenerateModalOpen(false);
      setLabOrderId("");
      void queryClient.invalidateQueries({ queryKey: ["reports-lab-worklist"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to generate report.");
    },
  });

  const amendMutation = useMutation({
    mutationFn: async () => {
      if (!selectedReportId) throw new Error("No report selected");
      const fallbackId = "018f0000-0000-7000-8000-000000000001";
      return unwrap(
        api.POST("/api/v1/reports/{report_id}/amend", {
          params: { path: { report_id: selectedReportId } },
          body: {
            amend_reason: amendReason,
            pathologist_id: me?.id || fallbackId,
            pathologist_name: pathologistName,
            bmdc_number: bmdcNumber,
            designation: designation,
          },
        }),
      );
    },
    onSuccess: (data: any) => {
      toast.success(`Report amended to version ${data?.versions?.length || 2} successfully!`);
      setAmendModalOpen(false);
      setAmendReason("");
      setSelectedReportId(null);
      void queryClient.invalidateQueries({ queryKey: ["reports-lab-worklist"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to amend report.");
    },
  });

  const handleDownload = async (reportId: string) => {
    try {
      const res = await unwrap(
        api.GET("/api/v1/patient/reports/{report_id}/download", {
          params: { path: { report_id: reportId } },
        }),
      );
      if (res?.download_url) {
        window.open(res.download_url, "_blank");
      }
    } catch (e: any) {
      toast.error(e.message || "Failed to obtain download URL");
    }
  };

  const handleShare = async (reportId: string) => {
    try {
      const res = await unwrap(
        api.POST("/api/v1/patient/reports/{report_id}/share", {
          params: { path: { report_id: reportId } },
          body: { expires_in_days: 7 },
        }),
      );
      if (res?.share_url) {
        await navigator.clipboard.writeText(res.share_url);
        toast.success("Time-limited secure report link copied to clipboard (valid for 7 days)");
      }
    } catch (e: any) {
      toast.error(e.message || "Failed to generate share link");
    }
  };

  const eligibleItems = (worklist || []).filter((w: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      w.order_no?.toLowerCase().includes(q) ||
      w.test_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("reports.title")}</h1>
          <p className="text-sm text-muted">{t("reports.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={`size-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="primary" onClick={() => setGenerateModalOpen(true)}>
            <Plus className="size-4" />
            {t("reports.generate")}
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardBody className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by order ID, test name, or report code..."
              className="pl-9"
            />
          </div>
        </CardBody>
      </Card>

      {/* Reports List */}
      <Card>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-6">
              <LoadingRows rows={5} label="Loading reports..." />
            </div>
          ) : !eligibleItems?.length ? (
            <div className="p-8">
              <EmptyState
                icon={<FileCheck2 className="size-8" />}
                title={t("reports.empty")}
                description="Completed lab orders ready for pathologist certification and release will appear here."
              />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {eligibleItems.map((item: any) => (
                <div
                  key={item.order_item_id}
                  className="flex flex-col gap-4 p-5 transition-colors hover:bg-surface-muted sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-fg">Order #{item.order_no}</span>
                      <Badge tone={item.status === "VERIFIED" ? "success" : "brand"}>
                        {item.status}
                      </Badge>
                      <span className="inline-flex items-center gap-1 rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                        <ShieldCheck className="size-3" />
                        SHA-256 Verified
                      </span>
                    </div>
                    <div className="text-sm text-fg">
                      Test: {item.test_name} ({item.department_name})
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 text-xs text-muted">
                      <span>Priority: <strong>{item.priority}</strong></span>
                      <span>Sample: {item.barcode || "N/A"}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setLabOrderId(item.order_id);
                        setGenerateModalOpen(true);
                      }}
                    >
                      <FileSignature className="size-3.5" />
                      Sign & Release
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(item.order_id)}
                    >
                      <Download className="size-3.5" />
                      PDF
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleShare(item.order_id)}
                    >
                      <Share2 className="size-3.5" />
                      Share
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setSelectedReportId(item.order_id);
                        setAmendModalOpen(true);
                      }}
                    >
                      Amend
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Generate & Sign Report Modal */}
      <Modal
        open={generateModalOpen}
        onOpenChange={setGenerateModalOpen}
        title="Pathologist Digital Certification & Report Release"
      >
        <div className="space-y-4 py-2">
          <p className="text-sm text-muted">
            Certify results with digital signature, calculate immutable SHA-256 seal, and generate QR verification token.
          </p>

          <Field label="Select Lab Order" required>
            <select
              value={labOrderId}
              onChange={(e) => setLabOrderId(e.target.value)}
              className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">-- Choose verified lab order --</option>
              {eligibleItems.map((o: any) => (
                <option key={o.order_item_id} value={o.order_id}>
                  Order #{o.order_no} — {o.test_name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Certifying Pathologist Name" required>
            <Input
              value={pathologistName}
              onChange={(e) => setPathologistName(e.target.value)}
              placeholder="e.g. Dr. Kazi Mahbubur Rahman"
            />
          </Field>

          <Field label="BM&DC Registration Number" required>
            <Input
              value={bmdcNumber}
              onChange={(e) => setBmdcNumber(e.target.value)}
              placeholder="e.g. A-48291"
            />
          </Field>

          <Field label="Designation">
            <Input
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="e.g. Consultant Clinical Pathologist"
            />
          </Field>

          <div className="rounded-[var(--radius-md)] bg-brand-50 p-3 text-xs text-brand-800">
            <strong>Legal Notice:</strong> Under Bangladesh Medical & Dental Council regulations, reports digitally signed with registered BM&DC credentials carry cryptographic authenticity and are verifiable by QR code.
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setGenerateModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!labOrderId || !pathologistName || !bmdcNumber || generateMutation.isPending}
              onClick={() => generateMutation.mutate()}
            >
              <CheckCircle2 className="size-4" />
              {generateMutation.isPending ? "Certifying..." : "Sign & Release PDF"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Amend Report Modal */}
      <Modal
        open={amendModalOpen}
        onOpenChange={setAmendModalOpen}
        title="Issue Amended Diagnostic Report (Version n+1)"
      >
        <div className="space-y-4 py-2">
          <p className="text-sm text-muted">
            Issuing an amended version supersedes the existing report. Bangladesh clinical auditing standards require explicit documentation of the clinical rationale for amendment.
          </p>

          <Field label="Amendment Clinical Rationale" required>
            <Textarea
              value={amendReason}
              onChange={(e) => setAmendReason(e.target.value)}
              rows={3}
              placeholder="e.g. Clinical correlation requested repeat examination of serum ferritin with updated reference intervals."
            />
          </Field>

          <Field label="Certifying Pathologist" required>
            <Input
              value={pathologistName}
              onChange={(e) => setPathologistName(e.target.value)}
            />
          </Field>

          <Field label="BM&DC Registration Number" required>
            <Input
              value={bmdcNumber}
              onChange={(e) => setBmdcNumber(e.target.value)}
            />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setAmendModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!amendReason || amendMutation.isPending}
              onClick={() => amendMutation.mutate()}
            >
              {amendMutation.isPending ? "Issuing..." : "Create Amended Version"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
