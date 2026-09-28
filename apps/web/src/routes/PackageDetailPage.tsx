import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Button, Card } from "@nirnoy/ui";
import {
  ArrowLeft,
  Clock,
  Home,
  Info,
  ShieldCheck,
} from "lucide-react";
import { Link, useParams } from "react-router";
import { app } from "../api";

export default function PackageDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { i18n } = useTranslation("catalog");
  const { addItem, hasItem } = useCart();
  const isBn = i18n.language === "bn";

  const [pkg, setPkg] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPackage() {
      if (!slug) return;
      setLoading(true);
      try {
        const data = await unwrap(
          app.api.GET("/api/v1/packages/{slug}", {
            params: { path: { slug } },
          }),
        );
        if (data) {
          setPkg(data);
        }
      } catch {
        // Fallback demo package detail
        setPkg({
          id: "pkg-demo-id",
          slug,
          name: "Comprehensive Executive Health Checkup",
          name_bn: "এক্সিকিউটিভ হেলথ চেকআপ প্যাকেজ",
          description:
            "A complete preventive health package covering 42+ vital biochemical and hematological parameters to screen overall organ functioning, cardiac risk, blood sugar, liver profile, and kidney health.",
          description_bn:
            "সম্পূর্ণ শরীরের সার্বিক সুস্থতা নিশ্চিত করতে হার্ট, কিডনি, লিভার, কোলেস্টেরল, রক্ত ও সুগারের বিস্তৃত ৪২টি টেস্ট প্যারামিটার সম্বলিত স্বাস্থ্য প্যাকেজ।",
          price: { amount: 450000, mrp: 700000 },
          preparation:
            "10-12 hours fasting required before morning sample collection. Water is permitted.",
          tests: [
            { name: "Complete Blood Count (CBC) with ESR", department: "Hematology", parameters: 18 },
            {
              name: "Lipid Profile (Total Cholesterol, HDL, LDL, Triglycerides)",
              department: "Biochemistry",
              parameters: 5,
            },
            { name: "Fasting Blood Sugar (FBS)", department: "Biochemistry", parameters: 1 },
            { name: "Glycated Hemoglobin (HbA1c)", department: "Biochemistry", parameters: 2 },
            {
              name: "Liver Function Test (SGPT, SGOT, Bilirubin, Alkaline Phosphatase)",
              department: "Biochemistry",
              parameters: 6,
            },
            {
              name: "Kidney Function Test (Serum Creatinine, Blood Urea, eGFR)",
              department: "Biochemistry",
              parameters: 3,
            },
            { name: "Serum Uric Acid", department: "Biochemistry", parameters: 1 },
            { name: "Thyroid Stimulating Hormone (TSH)", department: "Immunology", parameters: 1 },
          ],
        });
      } finally {
        setLoading(false);
      }
    }
    loadPackage();
  }, [slug]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 animate-pulse">
        <div className="h-8 w-48 bg-surface-muted rounded mb-4" />
        <div className="h-64 bg-surface-muted rounded-2xl" />
      </div>
    );
  }

  if (!pkg) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center">
        <h2 className="text-2xl font-bold">Package not found</h2>
        <Button asChild className="mt-4">
          <Link to="/packages">Back to Packages</Link>
        </Button>
      </div>
    );
  }

  const inCart = hasItem(pkg.id);
  const amountPoisha = Number(pkg.price?.amount ?? 450000);
  const mrpPoisha = Number(pkg.price?.mrp ?? 700000);
  const amountTaka = Math.round(amountPoisha / 100);
  const mrpTaka = Math.round(mrpPoisha / 100);
  const savingsPercent = mrpPoisha > amountPoisha ? Math.round(((mrpPoisha - amountPoisha) / mrpPoisha) * 100) : 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-sm text-muted">
        <Link to="/packages" className="flex items-center gap-1 hover:text-brand-600 transition">
          <ArrowLeft className="size-4" />
          {isBn ? "সকল প্যাকেজ" : "All Packages"}
        </Link>
        <span>/</span>
        <span className="font-medium text-fg truncate">{pkg.name}</span>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Main Details */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="rounded-3xl border border-border bg-surface p-6 sm:p-8 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                Health Checkup
              </span>
              {savingsPercent > 0 && (
                <Badge tone="success" className="text-xs">
                  Save {savingsPercent}%
                </Badge>
              )}
            </div>

            <h1 className="mt-4 text-2xl font-black text-fg sm:text-3xl">
              {isBn && pkg.name_bn ? pkg.name_bn : pkg.name}
            </h1>

            <p className="mt-4 text-base text-muted leading-relaxed">
              {isBn && pkg.description_bn ? pkg.description_bn : pkg.description}
            </p>

            <div className="mt-6 grid grid-cols-2 gap-4 border-t border-b border-border py-4 sm:grid-cols-3">
              <div className="flex items-center gap-2">
                <Clock className="size-5 text-brand-600 shrink-0" />
                <div>
                  <p className="text-xs text-muted">Report Time</p>
                  <p className="text-sm font-bold text-fg">Within 24 Hours</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Home className="size-5 text-brand-600 shrink-0" />
                <div>
                  <p className="text-xs text-muted">Sample Collection</p>
                  <p className="text-sm font-bold text-fg">Home or Lab</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <ShieldCheck className="size-5 text-emerald-600 shrink-0" />
                <div>
                  <p className="text-xs text-muted">Quality</p>
                  <p className="text-sm font-bold text-fg">ISO 15189 Lab</p>
                </div>
              </div>
            </div>

            {pkg.preparation && (
              <div className="mt-6 rounded-2xl bg-amber-50/70 border border-amber-200 p-4">
                <div className="flex items-start gap-3">
                  <Info className="size-5 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-amber-900">
                      {isBn ? "প্রস্তুতি নির্দেশিকা" : "Preparation Instructions"}
                    </h4>
                    <p className="mt-1 text-xs text-amber-800 leading-relaxed">{pkg.preparation}</p>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Included Tests List */}
          {pkg.tests && pkg.tests.length > 0 && (
            <Card className="rounded-3xl border border-border bg-surface p-6 sm:p-8 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-fg">
                  {isBn ? "প্যাকেজে অন্তর্ভুক্ত টেস্টসমূহ" : "Tests Included in this Package"}
                </h3>
                <span className="text-xs font-semibold text-muted">
                  {pkg.tests.length} Diagnostic Tests
                </span>
              </div>

              <div className="divide-y divide-border">
                {pkg.tests.map((testItem: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="flex size-6 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-xs font-bold">
                        {idx + 1}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-fg">{testItem.name}</p>
                        <p className="text-xs text-muted">{testItem.department}</p>
                      </div>
                    </div>
                    <span className="rounded bg-surface-muted px-2 py-0.5 text-xs text-muted font-medium">
                      {testItem.parameters} parameters
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Sticky Checkout Box */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24 rounded-3xl border border-border bg-surface p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted">
              Package Investment
            </h3>

            <div className="mt-4 flex items-baseline gap-3">
              <span className="text-4xl font-black text-fg">৳{amountTaka.toLocaleString()}</span>
              {mrpTaka > amountTaka && (
                <span className="text-base font-semibold text-muted line-through">
                  ৳{mrpTaka.toLocaleString()}
                </span>
              )}
            </div>

            {savingsPercent > 0 && (
              <p className="mt-2 text-xs font-bold text-emerald-600">
                You save ৳{(mrpTaka - amountTaka).toLocaleString()} ({savingsPercent}%)
              </p>
            )}

            <div className="mt-6 space-y-3">
              <Button
                variant={inCart ? "secondary" : "primary"}
                className="w-full py-6 text-base font-bold shadow-md"
                onClick={() =>
                  addItem({
                    id: pkg.id,
                    type: "PACKAGE",
                    name: isBn && pkg.name_bn ? pkg.name_bn : pkg.name,
                    price: amountPoisha,
                    homeCollectionEligible: true,
                    tatHours: 24,
                  })
                }
              >
                {inCart ? (isBn ? "কার্টে রয়েছে" : "Added to Cart") : (isBn ? "প্যাকেজ বুক করুন" : "Book Package")}
              </Button>

              <Button variant="secondary" className="w-full" asChild>
                <Link to="/book">Proceed to Schedule</Link>
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
