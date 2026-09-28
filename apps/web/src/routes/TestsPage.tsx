import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Button, Card } from "@nirnoy/ui";
import { Clock, Home, Info, Search, TestTube2 } from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { app } from "../api";

export default function TestsPage() {
  const { i18n } = useTranslation("catalog");
  const { addItem, hasItem } = useCart();
  const [searchParams] = useSearchParams();
  const isBn = i18n.language === "bn";

  const [tests, setTests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
  const [homeOnly, setHomeOnly] = useState(false);

  useEffect(() => {
    async function loadTests() {
      setLoading(true);
      try {
        const data = await unwrap(
          app.api.GET("/api/v1/tests", {
            params: {
              query: {
                q: searchQuery || undefined,
                home_collection_only: homeOnly || undefined,
                page_size: 50,
              },
            },
          }),
        );
        if (data) {
          setTests(data);
        }
      } catch {
        // Fallback demo items if backend offline
        setTests([
          {
            id: "cbc-1",
            slug: "cbc",
            name: "Complete Blood Count (CBC) with ESR",
            name_bn: "সিবিসি ও ইএসআর টেস্ট",
            department_name: "Hematology",
            tat_hours: 6,
            home_collection: true,
            preparation: "No fasting required",
            price: { amount: 60000, mrp: 75000 },
            parameters_count: 18,
          },
          {
            id: "lipid-1",
            slug: "lipid-profile",
            name: "Lipid Profile (Cholesterol Panel)",
            name_bn: "লিপিড প্রোফাইল",
            department_name: "Biochemistry",
            tat_hours: 12,
            home_collection: true,
            preparation: "10-12 hours fasting required",
            price: { amount: 120000, mrp: 150000 },
            parameters_count: 5,
          },
          {
            id: "fbs-1",
            slug: "fasting-blood-sugar",
            name: "Fasting Blood Sugar (Glucose)",
            name_bn: "ফাস্টিং ব্লাড সুগার",
            department_name: "Biochemistry",
            tat_hours: 4,
            home_collection: true,
            preparation: "8-10 hours fasting required",
            price: { amount: 25000, mrp: 30000 },
            parameters_count: 1,
          },
          {
            id: "hba1c-1",
            slug: "hba1c",
            name: "Glycated Hemoglobin (HbA1c)",
            name_bn: "এইচবিএওয়ানসি (৩ মাসের গড় সুগার)",
            department_name: "Biochemistry",
            tat_hours: 6,
            home_collection: true,
            preparation: "No fasting required",
            price: { amount: 100000, mrp: 120000 },
            parameters_count: 2,
          },
          {
            id: "tsh-1",
            slug: "tsh",
            name: "Thyroid Stimulating Hormone (TSH)",
            name_bn: "থাইরয়েড হরমোন (টিএসএইচ)",
            department_name: "Immunology",
            tat_hours: 12,
            home_collection: true,
            preparation: "Morning sample preferred",
            price: { amount: 80000, mrp: 100000 },
            parameters_count: 1,
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    loadTests();
  }, [searchQuery, homeOnly]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-fg sm:text-4xl">
          {isBn ? "ল্যাব টেস্ট সমূহ" : "Diagnostic Pathology Tests"}
        </h1>
        <p className="mt-2 text-base text-muted">
          {isBn
            ? "সকল অনুমোদিত নির্ভুল রক্ত ও ডায়াগনস্টিক পরীক্ষার তালিকা ও খরচ"
            : "Search and compare lab tests, preparation guidelines, and sample collection details."}
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted" />
          <input
            type="text"
            placeholder={isBn ? "টেস্টের নাম দিয়ে খুঁজুন..." : "Search tests by name or code..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-border bg-surface py-2 pl-9 pr-4 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={homeOnly ? "primary" : "secondary"}
            size="sm"
            onClick={() => setHomeOnly(!homeOnly)}
          >
            <Home className="size-4" />
            {isBn ? "হোম কালেকশন" : "Home Collection"}
          </Button>
        </div>
      </div>

      {/* Test List Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-64 animate-pulse rounded-2xl bg-surface-muted border border-border" />
          ))}
        </div>
      ) : tests.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border py-16 text-center">
          <TestTube2 className="mx-auto size-12 text-muted" />
          <h3 className="mt-4 text-lg font-semibold text-fg">
            {isBn ? "কোনো টেস্ট পাওয়া যায়নি" : "No tests found"}
          </h3>
          <p className="mt-1 text-sm text-muted">
            {isBn ? "অনুগ্রহ করে অন্য শব্দ দিয়ে চেষ্টা করুন" : "Try adjusting your search query or filters."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => {
            const inCart = hasItem(test.id);
            const pricePoisha = Number(test.price?.amount ?? (test.base_price ? test.base_price * 100 : 50000));
            const priceTaka = Math.round(pricePoisha / 100);
            return (
              <Card interactive
                key={test.id}
                className="flex flex-col justify-between overflow-hidden rounded-2xl border border-border bg-surface p-6 shadow-sm"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700">
                      {test.department_name || test.code || "Pathology"}
                    </span>
                    {(test.home_collection || test.is_home_collection_eligible) && (
                      <Badge tone="brand" className="text-xs">
                        <Home className="size-3 inline mr-1" /> Home Collection
                      </Badge>
                    )}
                  </div>

                  <h3 className="mt-3 text-lg font-bold text-fg leading-snug">
                    <Link
                      to={`/tests/${test.slug || test.id}`}
                      className="hover:text-brand-600 transition"
                    >
                      {isBn && test.name_bn ? test.name_bn : test.name}
                    </Link>
                  </h3>

                  {test.parameters_count && (
                    <p className="mt-1 text-xs text-muted font-medium">
                      Includes {test.parameters_count} key clinical parameters
                    </p>
                  )}

                  <div className="mt-4 space-y-2 text-xs text-muted">
                    <div className="flex items-center gap-2">
                      <Clock className="size-3.5 text-muted" />
                      <span>Report in {test.tat_hours || 24} hours</span>
                    </div>
                    {test.preparation && (
                      <div className="flex items-center gap-2">
                        <Info className="size-3.5 text-muted" />
                        <span className="line-clamp-1">{test.preparation}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 border-t border-border pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-2xl font-black tracking-tight text-fg">
                        ৳{priceTaka.toLocaleString()}
                      </span>
                    </div>
                    <Button
                      variant={inCart ? "secondary" : "primary"}
                      size="sm"
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
                      {inCart ? (isBn ? "কার্টে আছে" : "Added") : (isBn ? "কার্ট-এ যোগ করুন" : "Add to Cart")}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
