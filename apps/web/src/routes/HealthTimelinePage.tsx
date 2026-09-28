import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import {
  Badge,
  EmptyState,
  LoadingRows,
} from "@nirnoy/ui";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  Filter,
  HeartPulse,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";

export default function HealthTimelinePage() {
  const { api } = useAuth();

  const [selectedAnalyte, setSelectedAnalyte] = useState<string>("ALL");

  // 1. Fetch current patient profile
  const { data: patient, isLoading: patientLoading } = useQuery({
    queryKey: ["patient", "me"],
    queryFn: () => unwrap(api.GET("/api/v1/patients/me")),
  });

  // 2. Fetch patient analyte timeline
  const { data: timeline, isLoading: timelineLoading } = useQuery({
    queryKey: ["analytics", "patient-timeline", patient?.id],
    queryFn: () => {
      if (!patient?.id) return null;
      return unwrap(
        api.GET("/api/v1/analytics/patient/{patient_id}/timeline", {
          params: { path: { patient_id: patient.id } },
        })
      );
    },
    enabled: Boolean(patient?.id),
  });

  // Extract unique analytes / parameters for the filter tabs
  const availableAnalytes = useMemo(() => {
    if (!timeline?.readings) return [];
    const set = new Set<string>();
    for (const r of timeline.readings) {
      set.add(r.parameter_name);
    }
    return Array.from(set).sort();
  }, [timeline?.readings]);

  // Filtered readings
  const filteredReadings = useMemo(() => {
    if (!timeline?.readings) return [];
    if (selectedAnalyte === "ALL") return timeline.readings;
    return timeline.readings.filter((r) => r.parameter_name === selectedAnalyte);
  }, [timeline?.readings, selectedAnalyte]);

  const isLoading = patientLoading || timelineLoading;

  const getFlagBadge = (flag: string) => {
    switch (flag) {
      case "N":
        return <Badge tone="success">Normal</Badge>;
      case "H":
        return <Badge tone="warning">High</Badge>;
      case "L":
        return <Badge tone="warning">Low</Badge>;
      case "CH":
        return <Badge tone="danger">Critical High</Badge>;
      case "CL":
        return <Badge tone="danger">Critical Low</Badge>;
      case "ABN":
        return <Badge tone="danger">Abnormal</Badge>;
      default:
        return <Badge tone="neutral">{flag}</Badge>;
    }
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-8 sm:py-12">
      {/* Header */}
      <div className="flex flex-col gap-3">
        <Link
          to="/account"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-fg transition w-fit"
        >
          <ArrowLeft className="size-3.5" />
          Back to My Account
        </Link>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
              <HeartPulse className="size-6 text-brand" />
              Longitudinal Health Trends
            </h1>
            <p className="mt-1 text-sm text-muted">
              Track how your diagnostic biomarkers and laboratory analytes evolve over time.
            </p>
          </div>
        </div>
      </div>

      {isLoading ? (
        <LoadingRows rows={5} label="Loading your clinical health timeline..." />
      ) : !timeline || timeline.readings.length === 0 ? (
        <EmptyState
          icon={<HeartPulse className="size-10 text-muted" />}
          title="No Historical Test Trends Yet"
          description="Once your laboratory results are entered and verified by pathologists, your longitudinal analyte trends will appear here."
        />
      ) : (
        <div className="flex flex-col gap-6">
          {/* Summary Stat Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-subtle/50 p-4">
              <span className="text-xs font-medium uppercase tracking-wider text-muted">
                Total Investigations
              </span>
              <p className="mt-2 text-2xl font-bold text-foreground">
                {timeline.total_investigations}
              </p>
              <p className="mt-1 text-xs text-muted">Diagnostic lab test orders</p>
            </div>

            <div className="rounded-xl border border-border bg-subtle/50 p-4">
              <span className="text-xs font-medium uppercase tracking-wider text-muted">
                Tracked Biomarkers
              </span>
              <p className="mt-2 text-2xl font-bold text-brand">
                {availableAnalytes.length}
              </p>
              <p className="mt-1 text-xs text-muted">Measured clinical parameters</p>
            </div>

            <div className="rounded-xl border border-border bg-subtle/50 p-4">
              <span className="text-xs font-medium uppercase tracking-wider text-muted">
                Total Data Points
              </span>
              <p className="mt-2 text-2xl font-bold text-emerald-600">
                {timeline.readings.length}
              </p>
              <p className="mt-1 text-xs text-muted">Verified analyte observations</p>
            </div>
          </div>

          {/* Analyte Filter Pills */}
          {availableAnalytes.length > 1 && (
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-muted flex items-center gap-1.5">
                <Filter className="size-3.5" /> Filter by Biomarker:
              </span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  onClick={() => setSelectedAnalyte("ALL")}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    selectedAnalyte === "ALL"
                      ? "bg-brand text-white shadow-xs"
                      : "bg-subtle text-muted hover:bg-subtle/80 hover:text-foreground"
                  }`}
                >
                  All Analytes ({timeline.readings.length})
                </button>
                {availableAnalytes.map((analyte) => (
                  <button
                    key={analyte}
                    onClick={() => setSelectedAnalyte(analyte)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                      selectedAnalyte === analyte
                        ? "bg-brand text-white shadow-xs"
                        : "bg-subtle text-muted hover:bg-subtle/80 hover:text-foreground"
                    }`}
                  >
                    {analyte}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Longitudinal Timeline Stream */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">
              Chronological Observations ({filteredReadings.length})
            </h2>

            <div className="divide-y divide-border rounded-xl border border-border bg-surface overflow-hidden shadow-xs">
              {filteredReadings.map((reading, idx) => {
                const dateStr = new Date(reading.recorded_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                });
                const timeStr = new Date(reading.recorded_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                });
                const isAbnormal = reading.flag !== "N";

                return (
                  <div
                    key={`${reading.parameter_name}-${reading.recorded_at}-${idx}`}
                    className="flex flex-col justify-between gap-3 p-4 transition sm:flex-row sm:items-center hover:bg-subtle/30"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`rounded-lg p-2.5 ${
                          isAbnormal
                            ? "bg-red-50 text-red-700"
                            : "bg-emerald-50 text-emerald-700"
                        }`}
                      >
                        {isAbnormal ? (
                          <AlertTriangle className="size-4" />
                        ) : (
                          <Activity className="size-4" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground text-sm">
                            {reading.parameter_name}
                          </span>
                          {getFlagBadge(reading.flag)}
                        </div>
                        <p className="text-xs text-muted mt-0.5">
                          Test: {reading.test_name}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-6 pl-11 sm:pl-0">
                      <div className="text-left sm:text-right">
                        <span className="font-mono text-base font-bold text-foreground">
                          {reading.value}
                        </span>
                        <span className="ml-1 text-xs text-muted">{reading.unit}</span>
                      </div>

                      <div className="flex items-center gap-1.5 text-xs text-muted font-medium">
                        <Calendar className="size-3.5" />
                        <span>{dateStr}</span>
                        <span className="text-muted/60 text-[10px]">({timeStr})</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
