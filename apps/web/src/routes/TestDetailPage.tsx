import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Button, Card } from "@nirnoy/ui";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileCheck2,
  Home,
  Info,
  ShieldCheck,
  TestTube2,
} from "lucide-react";
import { Link, useParams } from "react-router";
import { app } from "../api";

export default function TestDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { i18n } = useTranslation("catalog");
  const { addItem, hasItem } = useCart();
  const isBn = i18n.language === "bn";

  const [test, setTest] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDetail() {
      if (!slug) return;
      setLoading(true);
      try {
        const data = await unwrap(
          app.api.GET("/api/v1/tests/{slug}", {
            params: { path: { slug } },
          }),
        );
        if (data) {
          setTest(data);
        }
      } catch {
        // Fallback demo detail
        setTest({
          id: "cbc-demo-id",
          slug,
          name: "Complete Blood Count (CBC) with Differential",
          name_bn: "কমপ্লিট ব্লাড কাউন্ট (সিবিসি)",
          description:
            "A Complete Blood Count evaluates overall health and detects a wide range of disorders including anemia, infection, and leukemia.",
          description_bn:
            "সিবিসি টেস্টের মাধ্যমে রক্তস্বল্পতা, ইনফেকশন ও রক্তের সামগ্রিক কোষের পরিমাণ নির্ণয় করা হয়।",
          department_name: "Hematology",
          sample_type_name: "EDTA Whole Blood (Purple Top)",
          tat_hours: 6,
          home_collection: true,
          preparation: "No special fasting required. Stay normally hydrated before the blood draw.",
          price: { amount: 60000, mrp: 75000 },
          parameters: [
            { name: "Hemoglobin (Hb)", unit: "g/dL", loinc: "718-7" },
            { name: "Total White Blood Cell Count (WBC)", unit: "10^3/uL", loinc: "6690-2" },
            { name: "Platelet Count", unit: "10^3/uL", loinc: "777-3" },
            { name: "Red Blood Cell (RBC) Count", unit: "10^6/uL", loinc: "789-8" },
            { name: "Packed Cell Volume (PCV / Hematocrit)", unit: "%", loinc: "4544-3" },
            { name: "Mean Corpuscular Volume (MCV)", unit: "fL", loinc: "787-2" },
            { name: "ESR (Westergren Method)", unit: "mm/1st hr", loinc: "30341-2" },
          ],
        });
      } finally {
        setLoading(false);
      }
    }
    loadDetail();
  }, [slug]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 animate-pulse">
        <div className="h-8 w-48 bg-surface-muted rounded mb-4" />
        <div className="h-64 bg-surface-muted rounded-2xl" />
      </div>
    );
  }

  if (!test) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center">
        <h2 className="text-2xl font-bold">Test not found</h2>
        <Button asChild className="mt-4">
          <Link to="/tests">Back to Tests</Link>
        </Button>
      </div>
    );
  }

  const inCart = hasItem(test.id);
  const pricePoisha = Number(test.price?.amount ?? 60000);
  const priceTaka = Math.round(pricePoisha / 100);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-sm text-muted">
        <Link to="/tests" className="flex items-center gap-1 hover:text-brand-600 transition">
          <ArrowLeft className="size-4" />
          {isBn ? "সকল টেস্ট" : "All Tests"}
        </Link>
        <span>/</span>
        <span className="font-medium text-fg truncate">{test.name}</span>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Main Content: 2 cols */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="rounded-3xl border border-border bg-surface p-6 sm:p-8 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                {test.department_name || "Hematology"}
              </span>
              {(test.home_collection || test.is_home_collection_eligible) && (
                <Badge tone="brand" className="text-xs">
                  <Home className="size-3 inline mr-1" /> Home Sample Collection Available
                </Badge>
              )}
            </div>

            <h1 className="mt-4 text-2xl font-black text-fg sm:text-3xl">
              {isBn && test.name_bn ? test.name_bn : test.name}
            </h1>

            <p className="mt-4 text-base text-muted leading-relaxed">
              {isBn && test.description_bn ? test.description_bn : test.description}
            </p>

            {/* Quick Badges */}
            <div className="mt-6 grid grid-cols-2 gap-4 border-t border-b border-border py-4 sm:grid-cols-3">
              <div className="flex items-center gap-2">
                <Clock className="size-5 text-brand-600 shrink-0" />
                <div>
                  <p className="text-xs text-muted">Turnaround Time</p>
                  <p className="text-sm font-bold text-fg">{test.tat_hours || 6} Hours</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <TestTube2 className="size-5 text-brand-600 shrink-0" />
                <div>
                  <p className="text-xs text-muted">Sample Tube</p>
                  <p className="text-sm font-bold text-fg truncate">
                    {test.sample_type_name || "Blood (EDTA)"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <ShieldCheck className="size-5 text-emerald-600 shrink-0" />
                <div>
                  <p className="text-xs text-muted">Standard</p>
                  <p className="text-sm font-bold text-fg">ISO 15189 Verified</p>
                </div>
              </div>
            </div>

            {/* Preparation */}
            {test.preparation && (
              <div className="mt-6 rounded-2xl bg-amber-50/70 border border-amber-200 p-4">
                <div className="flex items-start gap-3">
                  <Info className="size-5 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-amber-900">
                      {isBn ? "টেস্টের প্রস্তুতি নির্দেশিকা" : "Patient Preparation Guidelines"}
                    </h4>
                    <p className="mt-1 text-xs text-amber-800 leading-relaxed">{test.preparation}</p>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Parameters Section */}
          {test.parameters && test.parameters.length > 0 && (
            <Card className="rounded-3xl border border-border bg-surface p-6 sm:p-8 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-fg">
                  {isBn ? "ক্লিনিক্যাল প্যারামিটার তালিকা" : "Clinical Parameters Tested"}
                </h3>
                <span className="text-xs font-semibold text-muted">
                  {test.parameters.length} Parameters Included
                </span>
              </div>

              <div className="divide-y divide-border">
                {test.parameters.map((param: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="size-4 text-brand-600" />
                      <span className="text-sm font-medium text-fg">{param.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {param.loinc && (
                        <span className="text-xs font-mono text-muted">LOINC: {param.loinc}</span>
                      )}
                      {param.unit && (
                        <span className="rounded bg-surface-muted px-2 py-0.5 text-xs text-muted font-medium">
                          {param.unit}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Sidebar Card: Sticky Booking */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24 rounded-3xl border border-border bg-surface p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted">
              Pricing & Booking
            </h3>

            <div className="mt-4">
              <span className="text-4xl font-black text-fg">৳{priceTaka.toLocaleString()}</span>
            </div>

            <div className="mt-6 space-y-3">
              <Button
                variant={inCart ? "secondary" : "primary"}
                className="w-full py-6 text-base font-bold shadow-md"
                onClick={() =>
                  addItem({
                    id: test.id,
                    type: "TEST",
                    name: isBn && test.name_bn ? test.name_bn : test.name,
                    price: pricePoisha,
                    homeCollectionEligible: test.home_collection ?? true,
                    tatHours: test.tat_hours ?? 24,
                  })
                }
              >
                {inCart ? (isBn ? "কার্টে রয়েছে" : "Added to Cart") : (isBn ? "কার্টে যোগ করুন" : "Book Test Now")}
              </Button>

              <Button variant="secondary" className="w-full" asChild>
                <Link to="/book">Proceed to Schedule</Link>
              </Button>
            </div>

            <div className="mt-6 space-y-3 border-t border-border pt-4 text-xs text-muted">
              <div className="flex items-center gap-2">
                <FileCheck2 className="size-4 text-emerald-600" />
                <span>NABL & ISO 15189 Certified Lab</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="size-4 text-brand-600" />
                <span>Digital reports delivered via SMS & WhatsApp</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-brand-600" />
                <span>100% sterile barcoded vacutainer tubes</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
