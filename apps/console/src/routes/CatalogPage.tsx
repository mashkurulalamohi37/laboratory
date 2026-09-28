import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import {
  Badge,
  Card,
  CardBody,
  Input,
  LoadingRows,
} from "@nirnoy/ui";
import { useQuery } from "@tanstack/react-query";
import { Clock, FlaskConical, Package, Search } from "lucide-react";
import { useState } from "react";

export default function CatalogPage() {
  const { api } = useAuth();
  const [activeTab, setActiveTab] = useState<"tests" | "packages">("tests");
  const [search, setSearch] = useState("");

  const { data: tests, isLoading: testsLoading } = useQuery({
    queryKey: ["admin-catalog-tests", search],
    queryFn: () => unwrap(api.GET("/api/v1/tests", { params: { query: { q: search || undefined } } })),
    enabled: activeTab === "tests",
  });

  const { data: packages, isLoading: packagesLoading } = useQuery({
    queryKey: ["admin-catalog-packages"],
    queryFn: () => unwrap(api.GET("/api/v1/packages")),
    enabled: activeTab === "packages",
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Diagnostic Test & Package Catalog
          </h1>
          <p className="text-sm text-muted">
            Manage test definitions, clinical parameters, sample tubes, and package bundles.
          </p>
        </div>
      </div>

      <div className="flex border-b border-border">
        <button
          type="button"
          onClick={() => setActiveTab("tests")}
          className={`flex items-center gap-2 border-b-2 px-6 py-3 text-sm font-semibold transition ${
            activeTab === "tests"
              ? "border-brand text-brand"
              : "border-transparent text-muted hover:text-foreground"
          }`}
        >
          <FlaskConical className="size-4" />
          Individual Tests
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("packages")}
          className={`flex items-center gap-2 border-b-2 px-6 py-3 text-sm font-semibold transition ${
            activeTab === "packages"
              ? "border-brand text-brand"
              : "border-transparent text-muted hover:text-foreground"
          }`}
        >
          <Package className="size-4" />
          Health Packages
        </button>
      </div>

      {activeTab === "tests" && (
        <div className="space-y-4">
          <div className="relative max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <Input
              placeholder="Search tests by code, name, sample type..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {testsLoading ? (
            <LoadingRows rows={5} label="Loading test catalog..." />
          ) : !tests || tests.length === 0 ? (
            <Card>
              <CardBody className="py-8 text-center text-muted">No tests found.</CardBody>
            </Card>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Test Code & Name</th>
                    <th className="px-4 py-3 font-semibold">Department</th>
                    <th className="px-4 py-3 font-semibold">Sample Type</th>
                    <th className="px-4 py-3 font-semibold">Turnaround</th>
                    <th className="px-4 py-3 font-semibold">Home Collection</th>
                    <th className="px-4 py-3 font-semibold">Base Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {tests.map((t: any) => (
                    <tr key={t.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs font-bold text-brand">{t.code}</span>
                        <p className="font-semibold text-foreground">{t.name}</p>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">
                        {t.department_name || "Clinical Pathology"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone="neutral">{t.sample_type_name || "Blood"}</Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">
                        <span className="inline-flex items-center gap-1">
                          <Clock className="size-3" />
                          {t.tat_hours ? `${t.tat_hours} hrs` : "24 hrs"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {t.home_collection ? (
                          <span className="text-emerald-600 font-semibold">Eligible</span>
                        ) : (
                          <span className="text-muted">Lab Only</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono font-bold text-foreground">
                        ৳{Number(t.price?.amount ? t.price.amount / 100 : 500).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "packages" && (
        <div className="space-y-4">
          {packagesLoading ? (
            <LoadingRows rows={4} label="Loading health packages..." />
          ) : !packages || packages.length === 0 ? (
            <Card>
              <CardBody className="py-8 text-center text-muted">No health packages found.</CardBody>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {packages.map((p: any) => (
                <Card key={p.id} className="border border-border">
                  <CardBody className="p-5">
                    <div className="mb-2 flex items-center justify-between">
                      <Badge tone="brand">{p.slug || "PACKAGE"}</Badge>
                      <span className="font-mono text-sm font-bold text-emerald-600">
                        ৳{Number(p.price?.amount ? p.price.amount / 100 : 2500).toLocaleString()}
                      </span>
                    </div>
                    <h3 className="font-bold text-foreground">{p.name}</h3>
                    <p className="mt-1 line-clamp-2 text-xs text-muted">
                      {p.description || "Comprehensive checkup bundle tailored for diagnostic precision."}
                    </p>
                    <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted">
                      <span>{p.test_count || p.tests_count || "Multiple"} Tests included</span>
                      <span>TAT: {p.tat_hours ? `${p.tat_hours}h` : "24h"}</span>
                    </div>
                  </CardBody>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
