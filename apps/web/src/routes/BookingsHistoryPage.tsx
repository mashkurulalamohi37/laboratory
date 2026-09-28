import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { Badge, Button, Card, CardBody, LoadingRows, toast } from "@nirnoy/ui";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar,
  Clock,
  Home,
  MapPin,
  RefreshCw,
  Building2,
  AlertCircle,
} from "lucide-react";
import { Link } from "react-router";

export default function BookingsHistoryPage() {
  const { api } = useAuth();

  const {
    data: bookings,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["my-bookings"],
    queryFn: () => unwrap(api.GET("/api/v1/bookings/me")),
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

  const getPaymentBadge = (status: string) => {
    switch (status) {
      case "PAID":
        return <Badge tone="success">Paid</Badge>;
      case "PENDING":
        return <Badge tone="warning">Payment Pending</Badge>;
      case "REFUNDED":
        return <Badge tone="neutral">Refunded</Badge>;
      case "FAILED":
        return <Badge tone="danger">Failed</Badge>;
      default:
        return <Badge tone="neutral">{status}</Badge>;
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted">
            <Link to="/account" className="hover:underline">
              Account
            </Link>
            <span>/</span>
            <span>My Bookings</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Booking History</h1>
          <p className="mt-1 text-sm text-muted">
            Track your appointments, home sample collections, and lab report statuses.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void refetch();
              toast.success("Refreshed bookings");
            }}
            loading={isFetching}
          >
            <RefreshCw className="size-4" />
            Refresh
          </Button>
          <Button size="sm" asChild>
            <Link to="/book">Book New Test</Link>
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingRows rows={4} label="Loading your bookings..." />
      ) : isError ? (
        <Card>
          <CardBody className="py-12 text-center">
            <AlertCircle className="mx-auto mb-3 size-10 text-danger" />
            <h3 className="text-lg font-semibold text-foreground">Could not load bookings</h3>
            <p className="mt-1 text-sm text-muted">Please verify your connection and try again.</p>
            <Button variant="secondary" className="mt-4" onClick={() => void refetch()}>
              Retry
            </Button>
          </CardBody>
        </Card>
      ) : !bookings || bookings.length === 0 ? (
        <Card>
          <CardBody className="py-16 text-center">
            <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-brand/10 text-brand">
              <Calendar className="size-8" />
            </div>
            <h3 className="text-xl font-bold text-foreground">No bookings found</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted">
              You haven't booked any diagnostic tests or health checkup packages yet.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <Button asChild>
                <Link to="/tests">Browse Tests</Link>
              </Button>
              <Button variant="secondary" asChild>
                <Link to="/packages">Health Packages</Link>
              </Button>
            </div>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-6">
          {bookings.map((b: any) => (
            <Card interactive key={b.id} className="overflow-hidden border border-border shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-subtle/50 px-6 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-mono text-sm font-bold text-foreground">
                    #{b.booking_number}
                  </span>
                  <span className="text-xs text-muted">
                    Booked on {new Date(b.created_at).toLocaleDateString("en-GB", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(b.status)}
                  {getPaymentBadge(b.payment_status)}
                </div>
              </div>

              <CardBody className="p-6">
                <div className="grid gap-6 md:grid-cols-3">
                  {/* Schedule & Mode */}
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Schedule Details
                    </p>
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <Calendar className="size-4 text-brand" />
                      <span>{b.slot_date}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted">
                      <Clock className="size-4 text-muted" />
                      <span>{b.slot_time_range || "Scheduled Time Slot"}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-2 text-xs font-medium text-foreground">
                      {b.fulfillment_type === "HOME_COLLECTION" ? (
                        <>
                          <Home className="size-4 text-brand" />
                          <span className="rounded bg-brand/10 px-2 py-0.5 text-brand font-semibold">
                            Home Sample Collection
                          </span>
                        </>
                      ) : (
                        <>
                          <Building2 className="size-4 text-muted" />
                          <span className="rounded bg-subtle px-2 py-0.5 text-muted font-semibold">
                            Lab Visit (Walk-in)
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Patient Info */}
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Patient Details
                    </p>
                    <p className="text-sm font-semibold text-foreground">{b.patient_name}</p>
                    <p className="text-xs text-muted">
                      {b.patient_gender} • {b.patient_age} yrs
                    </p>
                    {b.collection_address && (
                      <p className="flex items-start gap-1 text-xs text-muted">
                        <MapPin className="size-3.5 shrink-0 text-muted mt-0.5" />
                        <span>
                          {b.collection_address.street_address}, {b.collection_address.area}
                        </span>
                      </p>
                    )}
                  </div>

                  {/* Financial & Items */}
                  <div className="space-y-2 md:text-right">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Total Amount
                    </p>
                    <p className="text-2xl font-bold tabular-nums text-foreground">
                      ৳{Number(b.total_amount).toLocaleString()}
                    </p>
                    {Number(b.discount_amount) > 0 && (
                      <p className="text-xs text-emerald-600 font-medium">
                        Discount: -৳{Number(b.discount_amount).toLocaleString()}
                      </p>
                    )}
                    <p className="text-xs text-muted">
                      {b.items?.length || 1} Item(s) included
                    </p>
                  </div>
                </div>

                {/* Items List */}
                {b.items && b.items.length > 0 && (
                  <div className="mt-6 rounded-xl border border-border bg-subtle/30 p-4">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted">
                      Tests / Packages Included
                    </p>
                    <ul className="divide-y divide-border">
                      {b.items.map((item: any) => (
                        <li key={item.id} className="flex items-center justify-between py-2 text-sm">
                          <span className="font-medium text-foreground">{item.item_name}</span>
                          <span className="font-mono text-muted tabular-nums">
                            ৳{Number(item.final_price).toLocaleString()}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
