import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import {
  Badge,
  Button,
  Card,
  CardBody,
  Input,
  LoadingRows,
  Select,
} from "@nirnoy/ui";
import { useQuery } from "@tanstack/react-query";
import {
  Home,
  RefreshCw,
  Search,
} from "lucide-react";
import { useState } from "react";

export default function BookingsPage() {
  const { api } = useAuth();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const {
    data: bookings,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["admin-bookings", statusFilter],
    queryFn: () => unwrap(api.GET("/api/v1/admin/bookings")),
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONFIRMED":
        return <Badge tone="brand">Confirmed</Badge>;
      case "COLLECTED":
        return <Badge tone="neutral">Sample Collected</Badge>;
      case "PROCESSING":
        return <Badge tone="neutral">Processing</Badge>;
      case "COMPLETED":
        return <Badge tone="success">Completed</Badge>;
      case "CANCELLED":
        return <Badge tone="danger">Cancelled</Badge>;
      default:
        return <Badge tone="neutral">{status}</Badge>;
    }
  };

  const filteredBookings = (bookings || []).filter((b: any) => {
    if (statusFilter && b.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchNum = b.booking_number?.toLowerCase().includes(q);
      const matchName = b.patient_name?.toLowerCase().includes(q);
      const matchPhone = b.contact_phone?.toLowerCase().includes(q);
      if (!matchNum && !matchName && !matchPhone) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Booking & Order Operations
          </h1>
          <p className="text-sm text-muted">
            Manage lab test orders, scheduled home collections, and fulfillment updates.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void refetch()}
          loading={isFetching}
        >
          <RefreshCw className="size-4" />
          Refresh
        </Button>
      </div>

      <Card>
        <CardBody className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="relative min-w-64 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Search by booking #, patient name, or phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="w-48">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="COLLECTED">Collected</option>
                <option value="PROCESSING">Processing</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </Select>
            </div>
          </div>
        </CardBody>
      </Card>

      {isLoading ? (
        <LoadingRows rows={5} label="Loading bookings..." />
      ) : isError ? (
        <Card>
          <CardBody className="py-8 text-center text-danger">
            Failed to load bookings.
          </CardBody>
        </Card>
      ) : filteredBookings.length === 0 ? (
        <Card>
          <CardBody className="py-12 text-center text-muted">
            No bookings match the selected criteria.
          </CardBody>
        </Card>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Booking #</th>
                <th className="px-4 py-3 font-semibold">Patient</th>
                <th className="px-4 py-3 font-semibold">Fulfillment</th>
                <th className="px-4 py-3 font-semibold">Schedule</th>
                <th className="px-4 py-3 font-semibold">Amount</th>
                <th className="px-4 py-3 font-semibold">Payment</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border font-medium">
              {filteredBookings.map((b: any) => (
                <tr key={b.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                  <td className="px-4 py-3 font-mono font-bold text-foreground">
                    {b.booking_number}
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-foreground">{b.patient_name}</p>
                    <p className="text-xs text-muted">
                      {b.patient_gender}, {b.patient_age}y • {b.contact_phone}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    {b.fulfillment_type === "HOME_COLLECTION" ? (
                      <span className="inline-flex items-center gap-1 rounded bg-brand/10 px-2 py-0.5 text-xs font-semibold text-brand">
                        <Home className="size-3" /> Home Collection
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded bg-subtle px-2 py-0.5 text-xs font-semibold text-muted">
                        Lab Visit
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    <p className="font-semibold text-foreground">{b.slot_date}</p>
                    <p className="text-muted">{b.slot_time_range || "Standard Slot"}</p>
                  </td>
                  <td className="px-4 py-3 font-mono font-bold tabular-nums text-foreground">
                    ৳{Number(b.total_amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={b.payment_status === "PAID" ? "success" : "warning"}>
                      {b.payment_status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">{getStatusBadge(b.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
