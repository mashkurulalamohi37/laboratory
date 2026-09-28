import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Button, Card } from "@nirnoy/ui";
import { ArrowRight, CheckCircle2, HeartPulse, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { app } from "../api";

export default function PackagesPage() {
  const { i18n } = useTranslation("catalog");
  const { addItem, hasItem } = useCart();
  const isBn = i18n.language === "bn";

  const [packages, setPackages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTag, setSelectedTag] = useState<string>("ALL");

  useEffect(() => {
    async function loadPackages() {
      setLoading(true);
      try {
        const data = await unwrap(app.api.GET("/api/v1/packages"));
        if (data) {
          setPackages(data);
        }
      } catch {
        // Fallback demo packages
        setPackages([
          {
            id: "pkg-1",
            slug: "executive-health-package",
            name: "Comprehensive Executive Health Checkup",
            name_bn: "এক্সিকিউটিভ হেলথ চেকআপ প্যাকেজ",
            description:
              "Full body health checkup assessing heart, liver, kidney, blood sugar, lipid panel and vital vitamins.",
            description_bn:
              "সম্পূর্ণ শরীরের গুরুত্বপূর্ণ অর্গান (হার্ট, লিভার, কিডনি, রক্ত ও সুগার) স্ক্রিনিং প্যাকেজ।",
            price: { amount: 450000, mrp: 700000 },
            tests_count: 8,
            parameters_count: 42,
            target_group: "Full Body",
          },
          {
            id: "pkg-2",
            slug: "diabetes-care-package",
            name: "Advanced Diabetes Care & Monitoring",
            name_bn: "ডায়াবেটিস কেয়ার প্যাকেজ",
            description:
              "Essential tests for diabetic patients including HbA1c, FBS, Lipid Profile, Serum Creatinine and Urine Microalbumin.",
            description_bn:
              "ডায়াবেটিস নিয়ন্ত্রণে নিয়মিত ৩ মাসের গ্লুকোজ, কিডনি ও কোলেস্টেরল পরীক্ষা।",
            price: { amount: 220000, mrp: 350000 },
            tests_count: 5,
            parameters_count: 18,
            target_group: "Diabetes",
          },
          {
            id: "pkg-3",
            slug: "women-wellness-package",
            name: "Women Wellness & Hormone Profile",
            name_bn: "উইমেন ওয়েলনেস ও হরমোন প্রোফাইল",
            description:
              "Tailored screening for women including Thyroid, CBC, Vitamin D, Calcium, Iron profile, and reproductive health markers.",
            description_bn:
              "নারীদের রক্তস্বল্পতা, থাইরয়েড, হাড়ের ঘনত্ব ও হরমোন সম্পর্কিত বিশেষ স্বাস্থ্য প্যাকেজ।",
            price: { amount: 380000, mrp: 550000 },
            tests_count: 7,
            parameters_count: 30,
            target_group: "Women Health",
          },
          {
            id: "pkg-4",
            slug: "senior-citizen-health",
            name: "Senior Citizen Comprehensive Panel",
            name_bn: "প্রবীণ নাগরিকদের স্বাস্থ্য প্যাকেজ",
            description:
              "Specially designed for elderly health maintenance, bone density, prostate/cardiac health and organ function tests.",
            description_bn:
              "বয়োজ্যেষ্ঠদের জন্য হাড়, লিভার, কিডনি, হার্ট এবং রক্তের সম্পূর্ণ ডায়াগনস্টিক প্যাকেজ।",
            price: { amount: 490000, mrp: 750000 },
            tests_count: 9,
            parameters_count: 48,
            target_group: "Senior Citizen",
          },
          {
            id: "pkg-5",
            slug: "healthy-heart-screening",
            name: "Healthy Heart & Lipid Panel",
            name_bn: "হার্ট হেলথ স্ক্রিনিং প্যাকেজ",
            description:
              "Cardiovascular health check with Lipid Profile, Troponin-I, hs-CRP, CBC, and Electrolytes.",
            description_bn: "হৃদরোগের ঝুঁকি নিরূপণ ও কোলেস্টেরল মাত্রা পরীক্ষার বিশেষ প্যাকেজ।",
            price: { amount: 290000, mrp: 420000 },
            tests_count: 4,
            parameters_count: 16,
            target_group: "Heart",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    loadPackages();
  }, []);

  const tags = ["ALL", "Full Body", "Diabetes", "Women Health", "Senior Citizen", "Heart"];

  const filtered = selectedTag === "ALL"
    ? packages
    : packages.filter((p) => p.target_group === selectedTag);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8 max-w-3xl">
        <div className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">
          <Sparkles className="size-3.5" />
          {isBn ? "সাশ্রয়ী প্যাকেজ সমূহ" : "Comprehensive Bundles & Checkups"}
        </div>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-fg sm:text-4xl">
          {isBn ? "প্রিভেন্টিভ হেলথ চেকআপ প্যাকেজ" : "Preventive Health Packages"}
        </h1>
        <p className="mt-2 text-base text-muted">
          {isBn
            ? "আপনার ও পরিবারের সুস্বাস্থ্যে নিয়মিত স্বাস্থ্য পরীক্ষার আকর্ষণীয় প্যাকেজ ও সর্বোচ্চ ৫০% পর্যন্ত সাশ্রয়"
            : "Save up to 50% with curated health checkup packages covering all major vital organs and health conditions."}
        </p>
      </div>

      {/* Filter Chips */}
      <div className="mb-8 flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Button
            key={tag}
            variant={selectedTag === tag ? "primary" : "secondary"}
            size="sm"
            onClick={() => setSelectedTag(tag)}
          >
            {tag === "ALL" ? (isBn ? "সব প্যাকেজ" : "All Packages") : tag}
          </Button>
        ))}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-80 animate-pulse rounded-2xl bg-surface-muted border border-border" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((pkg) => {
            const inCart = hasItem(pkg.id);
            const amountPoisha = Number(pkg.price?.amount ?? 350000);
            const mrpPoisha = Number(pkg.price?.mrp ?? amountPoisha * 1.4);
            const amountTaka = Math.round(amountPoisha / 100);
            const mrpTaka = Math.round(mrpPoisha / 100);
            const savingsPercent = mrpPoisha > amountPoisha ? Math.round(((mrpPoisha - amountPoisha) / mrpPoisha) * 100) : 0;

            return (
              <Card interactive
                key={pkg.id}
                className="flex flex-col justify-between overflow-hidden rounded-3xl border border-border bg-surface p-6 shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700">
                      {pkg.target_group || "Health Package"}
                    </span>
                    {savingsPercent > 0 && (
                      <Badge tone="success" className="text-xs">
                        {savingsPercent}% OFF
                      </Badge>
                    )}
                  </div>

                  <h3 className="mt-4 text-xl font-bold text-fg leading-snug">
                    <Link
                      to={`/packages/${pkg.slug || pkg.id}`}
                      className="hover:text-brand-600 transition"
                    >
                      {isBn && pkg.name_bn ? pkg.name_bn : pkg.name}
                    </Link>
                  </h3>

                  <p className="mt-2 text-xs text-muted line-clamp-2 leading-relaxed">
                    {isBn && pkg.description_bn ? pkg.description_bn : pkg.description}
                  </p>

                  <div className="mt-6 space-y-2 rounded-2xl bg-surface-muted p-3 text-xs font-medium text-fg">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="size-4 text-emerald-600 shrink-0" />
                      <span>{pkg.tests_count || 6} Specialized Tests Included</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <HeartPulse className="size-4 text-brand-600 shrink-0" />
                      <span>{pkg.parameters_count || 25}+ Clinical Parameters Analyzed</span>
                    </div>
                  </div>
                </div>

                <div className="mt-6 border-t border-border pt-4">
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-black text-fg">
                      ৳{amountTaka.toLocaleString()}
                    </span>
                    {mrpTaka > amountTaka && (
                      <span className="text-sm font-semibold text-muted line-through">
                        ৳{mrpTaka.toLocaleString()}
                      </span>
                    )}
                  </div>

                  <div className="mt-4 flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="flex-1"
                      asChild
                    >
                      <Link to={`/packages/${pkg.slug || pkg.id}`}>
                        {isBn ? "বিস্তারিত" : "Details"}
                        <ArrowRight className="size-3.5 ml-1" />
                      </Link>
                    </Button>

                    <Button
                      variant={inCart ? "secondary" : "primary"}
                      size="sm"
                      className="flex-1"
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
                      {inCart ? (isBn ? "কার্টে আছে" : "Added") : (isBn ? "যোগ করুন" : "Add to Cart")}
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
