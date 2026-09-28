import { useEffect, useState } from "react";
import { useParams, Link } from "react-router";
import { unwrap } from "@nirnoy/api-client";
import { Badge, Button, Card, CardBody, Spinner } from "@nirnoy/ui";
import {
  AlertTriangle,
  Award,
  Calendar,
  CheckCircle2,
  FileCheck,
  Lock,
  ShieldCheck,
  User,
} from "lucide-react";
import { app } from "../api";

interface VerificationData {
  is_valid: boolean;
  report_code: string;
  version_no: number;
  patient_masked_name: string;
  tests_included: string[];
  generated_at: string;
  verified_by_pathologist: string;
  bmdc_number: string;
}

export default function ReportVerificationPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<VerificationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function verify() {
      if (!token) {
        setError("Missing verification token");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const res = await unwrap(
          app.api.GET("/api/v1/verify/reports/{token}", {
            params: { path: { token } },
          }),
        );
        setData(res);
      } catch (err: any) {
        setError(err.message || "Unable to verify diagnostic report.");
      } finally {
        setLoading(false);
      }
    }

    void verify();
  }, [token]);

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      {/* Title Header */}
      <div className="mb-8 text-center">
        <div className="inline-flex size-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 shadow-sm">
          <ShieldCheck className="size-8" />
        </div>
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-fg sm:text-3xl">
          Report Authenticity Verification
        </h1>
        <p className="mt-2 text-sm text-muted">
          Public QR cryptographic certificate verification for Nirnoy Diagnostics clinical reports
        </p>
      </div>

      {loading ? (
        <Card>
          <CardBody className="p-8 text-center">
            <div className="flex flex-col items-center justify-center gap-3">
              <Spinner label="Validating report..." className="size-8 text-brand-600" />
              <p className="text-sm font-medium text-muted">
                Validating cryptographic token against healthcare ledger...
              </p>
            </div>
          </CardBody>
        </Card>
      ) : error || !data || !data.is_valid ? (
        <Card className="border-danger/30 bg-danger-bg/30">
          <CardBody className="p-8 text-center">
            <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-danger-bg text-danger">
              <AlertTriangle className="size-6" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-fg">Verification Failed</h2>
            <p className="mt-2 text-sm text-muted">
              {error || "The requested verification token is invalid, expired, or has been revoked."}
            </p>
            <div className="mt-6">
              <Link to="/">
                <Button variant="secondary">Return to Home</Button>
              </Link>
            </div>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Authenticity Certificate Banner */}
          <Card className="border-success/30 bg-success-bg/20">
            <CardBody className="p-6">
              <div className="flex items-center gap-4">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-success-bg text-success">
                  <CheckCircle2 className="size-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-fg">Official Clinical Report Verified</h2>
                    <Badge tone="success">Authentic</Badge>
                  </div>
                  <p className="text-xs text-muted">
                    This document was digitally certified by a BM&DC registered pathologist and matches our secure ledger.
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Report Details */}
          <Card>
            <CardBody className="p-6 space-y-5">
              <div className="flex flex-col justify-between gap-2 border-b border-border pb-4 sm:flex-row sm:items-center">
                <div>
                  <span className="text-xs uppercase tracking-wider text-muted">Report Identifier</span>
                  <div className="text-xl font-bold font-mono text-fg">{data.report_code}</div>
                </div>
                <div className="sm:text-right">
                  <span className="text-xs uppercase tracking-wider text-muted">Document Version</span>
                  <div>
                    <Badge tone="brand">Version {data.version_no} (Final)</Badge>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <span className="text-xs text-muted flex items-center gap-1.5">
                    <User className="size-3.5" /> Patient Name (Protected)
                  </span>
                  <div className="font-semibold text-fg">{data.patient_masked_name}</div>
                  <p className="text-[11px] text-muted">Masked in compliance with DGHS patient privacy</p>
                </div>

                <div className="space-y-1">
                  <span className="text-xs text-muted flex items-center gap-1.5">
                    <Calendar className="size-3.5" /> Certified On
                  </span>
                  <div className="font-semibold text-fg">
                    {new Date(data.generated_at).toLocaleString("en-US", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-xs text-muted flex items-center gap-1.5">
                    <Award className="size-3.5" /> Certifying Pathologist
                  </span>
                  <div className="font-semibold text-fg">Dr. {data.verified_by_pathologist}</div>
                </div>

                <div className="space-y-1">
                  <span className="text-xs text-muted flex items-center gap-1.5">
                    <FileCheck className="size-3.5" /> BM&DC Registration
                  </span>
                  <div className="font-semibold font-mono text-fg">{data.bmdc_number}</div>
                </div>
              </div>

              {/* Tests Included */}
              <div className="space-y-2 border-t border-border pt-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Tests & Investigations Included
                </span>
                <div className="flex flex-wrap gap-2">
                  {data.tests_included?.map((t, idx) => (
                    <span
                      key={idx}
                      className="rounded-[var(--radius-md)] border border-border bg-surface-muted px-2.5 py-1 text-xs font-medium text-fg"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              {/* Cryptographic Seal Notice */}
              <div className="rounded-[var(--radius-md)] bg-surface-muted p-4 text-xs text-muted space-y-1">
                <div className="flex items-center gap-1.5 font-semibold text-fg">
                  <Lock className="size-3.5 text-brand-600" />
                  SHA-256 Tamper-Evident Digital Seal
                </div>
                <p>
                  Every released report generates an immutable cryptographic hash. Any modification or unauthorized alterations to the PDF render the digital certificate invalid.
                </p>
                <div className="pt-1 font-mono text-[11px] text-muted">
                  Token: {token}
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
}
