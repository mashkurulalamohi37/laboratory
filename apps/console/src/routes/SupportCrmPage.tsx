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
  CheckCircle2,
  Clock,
  Headphones,
  MessageSquare,
  Plus,
  Send,
} from "lucide-react";
import { useState } from "react";

export default function SupportCrmPage() {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  // New Ticket Modal
  const [ticketModalOpen, setTicketModalOpen] = useState(false);
  const [newPatientName, setNewPatientName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newSubject, setNewSubject] = useState("");
  const [newCategory, setNewCategory] = useState("REPORT");
  const [newPriority, setNewPriority] = useState<"LOW" | "NORMAL" | "HIGH" | "URGENT">("NORMAL");
  const [newDescription, setNewDescription] = useState("");

  // Reply Input
  const [replyMessage, setReplyMessage] = useState("");

  // Queries
  const { data: tickets, isLoading: ticketsLoading } = useQuery({
    queryKey: ["crm", "tickets", statusFilter, categoryFilter],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/crm/tickets", {
          params: {
            query: {
              status: statusFilter || undefined,
              category: categoryFilter || undefined,
            },
          },
        })
      ),
  });

  const { data: selectedTicket, isLoading: selectedLoading } = useQuery({
    queryKey: ["crm", "ticket", selectedTicketId],
    queryFn: () => {
      if (!selectedTicketId) return null;
      return unwrap(
        api.GET("/api/v1/crm/tickets/{ticket_id}", {
          params: { path: { ticket_id: selectedTicketId } },
        })
      );
    },
    enabled: Boolean(selectedTicketId),
  });

  // Mutations
  const createTicketMutation = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/crm/tickets", {
          body: {
            patient_name: newPatientName,
            phone: newPhone,
            subject: newSubject,
            category: newCategory,
            priority: newPriority,
            description: newDescription,
          },
        })
      ),
    onSuccess: (data) => {
      setTicketModalOpen(false);
      setNewPatientName("");
      setNewPhone("");
      setNewSubject("");
      setNewDescription("");
      if (data) setSelectedTicketId(data.id);
      void queryClient.invalidateQueries({ queryKey: ["crm", "tickets"] });
    },
  });

  const sendReplyMutation = useMutation({
    mutationFn: () => {
      if (!selectedTicketId || !replyMessage) return Promise.resolve(null);
      return unwrap(
        api.POST("/api/v1/crm/tickets/{ticket_id}/messages", {
          params: { path: { ticket_id: selectedTicketId } },
          body: {
            message: replyMessage,
          },
        })
      );
    },
    onSuccess: () => {
      setReplyMessage("");
      void queryClient.invalidateQueries({ queryKey: ["crm", "ticket", selectedTicketId] });
      void queryClient.invalidateQueries({ queryKey: ["crm", "tickets"] });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ status }: { status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED" }) => {
      if (!selectedTicketId) return Promise.resolve(null);
      return unwrap(
        api.PATCH("/api/v1/crm/tickets/{ticket_id}", {
          params: { path: { ticket_id: selectedTicketId } },
          body: { status },
        })
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["crm", "ticket", selectedTicketId] });
      void queryClient.invalidateQueries({ queryKey: ["crm", "tickets"] });
    },
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("crm.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("crm.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={() => setTicketModalOpen(true)}>
            <Plus className="size-4" />
            {t("crm.newTicket")}
          </Button>
        </div>
      </div>

      {/* Main Grid: Ticket Queue (Left) & Conversation Thread (Right) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Ticket List (5 cols) */}
        <div className="flex flex-col gap-4 lg:col-span-5">
          {/* Filter Bar */}
          <div className="grid grid-cols-2 gap-2">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </Select>

            <Select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="text-xs"
            >
              <option value="">All Categories</option>
              <option value="REPORT">Report Inquiry</option>
              <option value="BOOKING">Booking / Rescheduling</option>
              <option value="COLLECTION">Collection Delay</option>
              <option value="BILLING">Billing Dispute</option>
              <option value="GENERAL">General</option>
            </Select>
          </div>

          {/* List items */}
          {ticketsLoading ? (
            <LoadingRows rows={5} label="Loading support tickets..." />
          ) : !tickets || tickets.length === 0 ? (
            <EmptyState
              icon={<Headphones className="size-8" />}
              title={t("crm.empty")}
              description="No support or clinical inquiries matching the selected filters."
            />
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-surface overflow-hidden">
              {tickets.map((tkt) => {
                const isSelected = tkt.id === selectedTicketId;
                const isUrgent = tkt.priority === "URGENT" || tkt.priority === "HIGH";
                const isOverdue = tkt.sla_due_at && new Date(tkt.sla_due_at) < new Date() && tkt.status !== "RESOLVED";

                return (
                  <button
                    key={tkt.id}
                    onClick={() => setSelectedTicketId(tkt.id)}
                    className={`flex w-full flex-col p-4 text-left transition hover:bg-surface-muted/50 ${
                      isSelected ? "bg-brand-50/70 border-l-4 border-brand-600" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-semibold text-muted">
                        {tkt.ticket_no}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <Badge
                          tone={
                            tkt.status === "RESOLVED"
                              ? "success"
                              : tkt.status === "IN_PROGRESS"
                              ? "brand"
                              : "neutral"
                          }
                        >
                          {tkt.status}
                        </Badge>
                        <Badge tone={isUrgent ? "danger" : "neutral"}>
                          {tkt.priority}
                        </Badge>
                      </div>
                    </div>

                    <p className="mt-1 font-medium text-fg text-sm line-clamp-1">{tkt.subject}</p>

                    <div className="mt-2 flex items-center justify-between text-xs text-muted">
                      <span>{tkt.patient_name} · {tkt.category}</span>
                      {tkt.sla_due_at && (
                        <span
                          className={`flex items-center gap-1 ${
                            isOverdue ? "font-semibold text-red-600" : ""
                          }`}
                        >
                          <Clock className="size-3" />
                          {isOverdue ? "SLA Overdue" : "Due: " + new Date(tkt.sla_due_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Conversation Thread (7 cols) */}
        <div className="flex flex-col rounded-xl border border-border bg-surface lg:col-span-7">
          {!selectedTicketId ? (
            <div className="flex flex-1 flex-col items-center justify-center p-12 text-center text-muted">
              <MessageSquare className="size-12 stroke-[1.5]" />
              <p className="mt-3 text-sm font-medium text-fg">Select a ticket</p>
              <p className="mt-1 text-xs">
                Choose a ticket from the left queue to review its clinical or customer thread.
              </p>
            </div>
          ) : selectedLoading ? (
            <div className="p-6">
              <LoadingRows rows={4} label="Loading conversation thread..." />
            </div>
          ) : selectedTicket ? (
            <div className="flex flex-1 flex-col">
              {/* Thread Header */}
              <div className="border-b border-border p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-brand-700">
                        {selectedTicket.ticket_no}
                      </span>
                      <Badge tone={selectedTicket.priority === "URGENT" ? "danger" : "neutral"}>
                        {selectedTicket.priority}
                      </Badge>
                      <Badge tone="brand">{selectedTicket.category}</Badge>
                    </div>
                    <h2 className="mt-1 text-lg font-bold text-fg">{selectedTicket.subject}</h2>
                    <p className="mt-1 text-xs text-muted">
                      Patient: {selectedTicket.patient_name} ({selectedTicket.phone})
                    </p>
                  </div>

                  {/* Actions / Status changer */}
                  <div className="flex items-center gap-2">
                    {selectedTicket.status !== "RESOLVED" ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => updateStatusMutation.mutate({ status: "RESOLVED" })}
                        loading={updateStatusMutation.isPending}
                      >
                        <CheckCircle2 className="size-3.5" />
                        Mark Resolved
                      </Button>
                    ) : (
                      <Badge tone="success">Resolved</Badge>
                    )}
                  </div>
                </div>
              </div>

              {/* Messages Scroll Area */}
              <div className="flex-1 space-y-4 p-4 overflow-y-auto max-h-[500px]">
                {/* Initial Description */}
                <div className="rounded-xl border border-border bg-surface-muted/30 p-3 text-sm">
                  <p className="text-xs font-semibold text-muted mb-1">Inquiry Description</p>
                  <p className="text-fg whitespace-pre-wrap">{selectedTicket.description}</p>
                </div>

                {selectedTicket.messages && selectedTicket.messages.length > 0 ? (
                  selectedTicket.messages.map((msg) => {
                    const isStaff = msg.is_staff;
                    return (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${isStaff ? "items-end" : "items-start"}`}
                      >
                        <div
                          className={`max-w-[85%] rounded-2xl p-4 text-sm shadow-xs ${
                            isStaff
                              ? "bg-brand-600 text-white rounded-br-xs"
                              : "bg-surface-muted text-fg rounded-bl-xs border border-border"
                          }`}
                        >
                          <div className="mb-1 flex items-center gap-2 text-xs opacity-80">
                            <span className="font-semibold">{msg.sender_name}</span>
                            <span>·</span>
                            <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                          <p className="whitespace-pre-wrap">{msg.message}</p>
                        </div>
                      </div>
                    );
                  })
                ) : null}
              </div>

              {/* Reply Box */}
              <div className="border-t border-border p-3">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    sendReplyMutation.mutate();
                  }}
                  className="flex items-center gap-2"
                >
                  <Input
                    value={replyMessage}
                    onChange={(e) => setReplyMessage(e.target.value)}
                    placeholder="Type reply to patient / staff note..."
                    className="flex-1"
                  />
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={!replyMessage}
                    loading={sendReplyMutation.isPending}
                  >
                    <Send className="size-4" />
                    {t("crm.reply")}
                  </Button>
                </form>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* New Ticket Modal */}
      <Modal
        open={ticketModalOpen}
        onOpenChange={setTicketModalOpen}
        title="Create Patient Support / Inquiry Ticket"
      >
        <div className="flex flex-col gap-4 p-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="crm-ticket-patient-name" className="text-xs font-medium text-muted">Patient Name</label>
              <Input
                id="crm-ticket-patient-name"
                value={newPatientName}
                onChange={(e) => setNewPatientName(e.target.value)}
                placeholder="e.g. Mohammad Rahim"
                className="mt-1"
              />
            </div>
            <div>
              <label htmlFor="crm-ticket-patient-phone" className="text-xs font-medium text-muted">Mobile Number</label>
              <Input
                id="crm-ticket-patient-phone"
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="017xxxxxxxx"
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <label htmlFor="crm-ticket-subject" className="text-xs font-medium text-muted">Subject / Summary</label>
            <Input
              id="crm-ticket-subject"
              value={newSubject}
              onChange={(e) => setNewSubject(e.target.value)}
              placeholder="e.g. Critical fasting blood sugar inquiry"
              className="mt-1"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="crm-ticket-category" className="text-xs font-medium text-muted">Category</label>
              <Select
                id="crm-ticket-category"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="mt-1"
              >
                <option value="REPORT">Report Inquiry</option>
                <option value="BOOKING">Booking / Rescheduling</option>
                <option value="COLLECTION">Collection Delay</option>
                <option value="BILLING">Billing Dispute</option>
                <option value="GENERAL">General</option>
              </Select>
            </div>

            <div>
              <label htmlFor="crm-ticket-priority" className="text-xs font-medium text-muted">Priority</label>
              <Select
                id="crm-ticket-priority"
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value as any)}
                className="mt-1"
              >
                <option value="LOW">Low</option>
                <option value="NORMAL">Normal (48h SLA)</option>
                <option value="HIGH">High (12h SLA)</option>
                <option value="URGENT">Urgent (4h SLA)</option>
              </Select>
            </div>
          </div>

          <div>
            <label htmlFor="crm-ticket-description" className="text-xs font-medium text-muted">Description / Inquiry</label>
            <textarea
              id="crm-ticket-description"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              rows={4}
              placeholder="Detailed description of the customer request or clinical finding..."
              className="mt-1 w-full rounded-lg border border-border bg-surface p-2.5 text-sm text-fg shadow-xs focus:border-brand-500 focus:outline-hidden"
            />
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setTicketModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!newPatientName || !newPhone || !newSubject || !newDescription}
              onClick={() => createTicketMutation.mutate()}
              loading={createTicketMutation.isPending}
            >
              Open Ticket
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
