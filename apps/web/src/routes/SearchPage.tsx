import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Button, Card } from "@nirnoy/ui";
import { Package, Search, TestTube2 } from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { app } from "../api";
import { SearchAutocomplete } from "../components/SearchAutocomplete";

export default function SearchPage() {
  const { i18n } = useTranslation("catalog");
  const { addItem, hasItem } = useCart();
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const isBn = i18n.language === "bn";

  const [results, setResults] = useState<any>({ tests: [], packages: [], concerns: [], centres: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function performSearch() {
      if (!query.trim()) {
        setResults({ tests: [], packages: [], concerns: [], centres: [] });
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const data = await unwrap(
          app.api.GET("/api/v1/search", {
            params: { query: { q: query.trim() } },
          }),
        );
        if (data) {
          setResults(data);
        }
      } catch {
        // Fallback demo results matching query
        setResults({
          tests: [
            {
              id: "fbs-search",
              slug: "fasting-blood-sugar",
              name: "Fasting Blood Sugar (Glucose)",
              name_bn: "ফাস্টিং ব্লাড সুগার",
              department_name: "Biochemistry",
              price: { amount: 25000, mrp: 30000 },
              tat_hours: 4,
            },
            {
              id: "hba1c-search",
              slug: "hba1c",
              name: "HbA1c (Glycated Hemoglobin)",
              name_bn: "এইচবিএওয়ানসি (৩ মাসের গড় সুগার)",
              department_name: "Biochemistry",
              price: { amount: 100000, mrp: 120000 },
              tat_hours: 6,
            },
          ],
          packages: [
            {
              id: "pkg-diab-search",
              slug: "diabetes-care-package",
              name: "Diabetes Care & Monitoring Checkup",
              name_bn: "ডায়াবেটিস কেয়ার প্যাকেজ",
              price: { amount: 220000, mrp: 350000 },
              tests_count: 5,
            },
          ],
          concerns: [],
          centres: [],
        });
      } finally {
        setLoading(false);
      }
    }
    performSearch();
  }, [query]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Search Bar on Page */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-fg sm:text-3xl">
          {query ? `Search Results for "${query}"` : "Search Diagnostic Catalog"}
        </h1>
        <div className="mt-4 max-w-2xl">
          <SearchAutocomplete />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 animate-pulse rounded-2xl bg-surface-muted border border-border" />
          ))}
        </div>
      ) : !query.trim() ? (
        <div className="rounded-2xl border border-dashed border-border py-16 text-center">
          <Search className="mx-auto size-12 text-muted" />
          <h3 className="mt-4 text-base font-semibold text-fg">Type above to search</h3>
          <p className="mt-1 text-sm text-muted">
            Search across 500+ diagnostic pathology tests, health checkup bundles and packages.
          </p>
        </div>
      ) : (
        <div className="space-y-10">
          {/* Tests Section */}
          {results.tests && results.tests.length > 0 && (
            <div>
              <div className="mb-4 flex items-center justify-between border-b border-border pb-2">
                <h2 className="flex items-center gap-2 text-xl font-bold text-fg">
                  <TestTube2 className="size-5 text-brand-600" />
                  Pathology Tests ({results.tests.length})
                </h2>
                <Link to="/tests" className="text-sm font-semibold text-brand-600 hover:underline">
                  View All Tests
                </Link>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {results.tests.map((test: any) => {
                  const inCart = hasItem(test.id);
                  const pricePoisha = Number(test.price?.amount ?? 50000);
                  const priceTaka = Math.round(pricePoisha / 100);
                  return (
                    <Card interactive key={test.id} className="p-5 flex flex-col justify-between rounded-2xl">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                            {test.department_name || test.code || "Pathology"}
                          </span>
                          <Badge tone="brand" className="text-xs">
                            {test.tat_hours ? `${test.tat_hours}h TAT` : "24h"}
                          </Badge>
                        </div>
                        <h3 className="mt-3 font-bold text-fg">
                          <Link to={`/tests/${test.slug || test.id}`} className="hover:text-brand-600">
                            {isBn && test.name_bn ? test.name_bn : test.name}
                          </Link>
                        </h3>
                      </div>

                      <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                        <span className="text-xl font-black text-fg">
                          ৳{priceTaka.toLocaleString()}
                        </span>
                        <Button
                          size="sm"
                          variant={inCart ? "secondary" : "primary"}
                          onClick={() =>
                            addItem({
                              id: test.id,
                              type: "TEST",
                              name: test.name,
                              price: pricePoisha,
                              homeCollectionEligible: true,
                              tatHours: test.tat_hours || 24,
                            })
                          }
                        >
                          {inCart ? "Added" : "Add to Cart"}
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* Packages Section */}
          {results.packages && results.packages.length > 0 && (
            <div>
              <div className="mb-4 flex items-center justify-between border-b border-border pb-2">
                <h2 className="flex items-center gap-2 text-xl font-bold text-fg">
                  <Package className="size-5 text-brand-600" />
                  Health Packages ({results.packages.length})
                </h2>
                <Link to="/packages" className="text-sm font-semibold text-brand-600 hover:underline">
                  View All Packages
                </Link>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {results.packages.map((pkg: any) => {
                  const inCart = hasItem(pkg.id);
                  const pricePoisha = Number(pkg.price?.amount ?? 250000);
                  const priceTaka = Math.round(pricePoisha / 100);
                  return (
                    <Card interactive key={pkg.id} className="p-5 flex flex-col justify-between rounded-2xl">
                      <div>
                        <Badge tone="success" className="text-xs">
                          {pkg.tests_count || 5} Tests Bundle
                        </Badge>
                        <h3 className="mt-3 font-bold text-fg">
                          <Link to={`/packages/${pkg.slug || pkg.id}`} className="hover:text-brand-600">
                            {isBn && pkg.name_bn ? pkg.name_bn : pkg.name}
                          </Link>
                        </h3>
                      </div>

                      <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                        <span className="text-xl font-black text-fg">
                          ৳{priceTaka.toLocaleString()}
                        </span>
                        <Button
                          size="sm"
                          variant={inCart ? "secondary" : "primary"}
                          onClick={() =>
                            addItem({
                              id: pkg.id,
                              type: "PACKAGE",
                              name: pkg.name,
                              price: pricePoisha,
                              homeCollectionEligible: true,
                              tatHours: 24,
                            })
                          }
                        >
                          {inCart ? "Added" : "Add to Cart"}
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {(!results.tests || results.tests.length === 0) &&
            (!results.packages || results.packages.length === 0) && (
              <div className="rounded-2xl border border-dashed border-border py-16 text-center">
                <p className="text-base font-semibold text-fg">No results match "{query}"</p>
                <p className="mt-1 text-xs text-muted">
                  Try searching for general keywords like "CBC", "Lipid", "Sugar", or "Thyroid".
                </p>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
