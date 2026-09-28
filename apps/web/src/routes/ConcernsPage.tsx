import { useTranslation } from "@nirnoy/i18n";
import { Button, Card } from "@nirnoy/ui";
import {
  Activity,
  ArrowRight,
  Droplet,
  HeartPulse,
  ShieldAlert,
  Sparkles,
  TestTube2,
  Zap,
} from "lucide-react";
import { Link } from "react-router";

const CONCERN_DATA = [
  {
    slug: "diabetes",
    name: "Diabetes & Metabolism",
    name_bn: "ডায়াবেটিস ও মেটাবলিজম",
    description: "Screening blood glucose levels, HbA1c, insulin resistance, and kidney complications.",
    description_bn: "রক্তের গ্লুকোজ, ৩ মাসের গড় সুগার ও কিডনির কার্যকারিতা পরীক্ষা।",
    icon: Activity,
    tests: ["Fasting Blood Sugar (FBS)", "HbA1c", "Lipid Profile"],
    packages: ["Diabetes Care Package"],
  },
  {
    slug: "heart",
    name: "Heart & Cardiovascular Health",
    name_bn: "হার্ট ও হৃদরোগ স্বাস্থ্য",
    description: "Assessment of cholesterol, triglycerides, cardiac enzymes, and hypertension markers.",
    description_bn: "কোলেস্টেরল, ট্রাইগ্লিসারাইড ও হৃদযন্ত্রের ঝুঁকি সম্পর্কিত ল্যাব পরীক্ষা।",
    icon: HeartPulse,
    tests: ["Lipid Profile", "Troponin I", "High Sensitivity CRP"],
    packages: ["Healthy Heart Screening"],
  },
  {
    slug: "thyroid",
    name: "Thyroid & Hormone Balance",
    name_bn: "থাইরয়েড ও হরমোন সমস্যা",
    description: "Evaluation of TSH, Free T3, Free T4 for hyperthyroidism and hypothyroidism symptoms.",
    description_bn: "থাইরয়েড গ্রন্থির হরমোন নিঃসরণ ও মেটাবলিজম ভারসাম্য পরীক্ষা।",
    icon: Sparkles,
    tests: ["TSH (Thyroid Stimulating Hormone)", "Free T3", "Free T4"],
    packages: ["Thyroid Care Bundle"],
  },
  {
    slug: "liver",
    name: "Liver Function & Hepatitis",
    name_bn: "লিভার ফাংশন ও হেপাটাইটিস",
    description: "Tests for jaundice, fatty liver, enzyme elevation, SGPT, SGOT, and viral hepatitis.",
    description_bn: "জন্ডিস, ফ্যাটি লিভার ও লিভার এনজাইম পরীক্ষা।",
    icon: Droplet,
    tests: ["Liver Function Test (LFT)", "SGPT / ALT", "HBsAg Screening"],
    packages: ["Liver Wellness Checkup"],
  },
  {
    slug: "kidney",
    name: "Kidney Function & Urinary Health",
    name_bn: "কিডনি ফাংশন ও প্রস্রাবের পরীক্ষা",
    description: "Tests for serum creatinine, urea, electrolytes, and routine urine microscopy.",
    description_bn: "কিডনির কার্যক্ষমতা ও রক্তে ক্রিয়েটিনিন ও ইউরিয়ার মাত্রা পরীক্ষা।",
    icon: Zap,
    tests: ["Serum Creatinine", "Blood Urea Nitrogen", "Urine Routine Examination"],
    packages: ["Renal Health Checkup"],
  },
  {
    slug: "fever",
    name: "Fever & Infection Panel",
    name_bn: "জ্বর ও ইনফেকশন প্যানেল",
    description: "Rapid diagnostics for Dengue NS1, Typhoid, Malaria, and complete blood count with ESR.",
    description_bn: "ডেঙ্গু, টাইফয়েড, ম্যালেরিয়া ও সাধারণ জ্বর-সংক্রমণ নির্ণয়।",
    icon: ShieldAlert,
    tests: ["Dengue NS1 Antigen", "Widal Test", "CBC with ESR"],
    packages: ["Fever Diagnostic Profile"],
  },
];

export default function ConcernsPage() {
  const { i18n } = useTranslation("catalog");
  const isBn = i18n.language === "bn";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-10 max-w-3xl">
        <div className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">
          <HeartPulse className="size-3.5" />
          {isBn ? "শারীরিক লক্ষণ ও স্বাস্থ্য সমস্যা" : "Symptoms & Health Conditions"}
        </div>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-fg sm:text-4xl">
          {isBn ? "স্বাস্থ্য সমস্যা অনুযায়ী পরীক্ষা খুঁজুন" : "Browse by Health Concern"}
        </h1>
        <p className="mt-2 text-base text-muted">
          {isBn
            ? "আপনার লক্ষণ বা শারীরিক অবস্থা নির্বাচন করে সংশ্লিষ্ট ডায়াগনস্টিক টেস্ট ও প্যাকেজ সহজে বেছে নিন।"
            : "Explore curated diagnostic tests and specialized checkup packages organized by organ systems and health risks."}
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {CONCERN_DATA.map((concern) => {
          const Icon = concern.icon;
          return (
            <Card interactive
              key={concern.slug}
              className="flex flex-col justify-between overflow-hidden rounded-3xl border border-border bg-surface p-6 shadow-sm"
            >
              <div>
                <div className="flex size-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
                  <Icon className="size-6" />
                </div>

                <h3 className="mt-4 text-xl font-bold text-fg">
                  {isBn ? concern.name_bn : concern.name}
                </h3>

                <p className="mt-2 text-xs text-muted leading-relaxed">
                  {isBn ? concern.description_bn : concern.description}
                </p>

                <div className="mt-5 space-y-2 border-t border-border pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-muted">
                    Recommended Tests
                  </p>
                  <ul className="space-y-1 text-xs font-medium text-fg">
                    {concern.tests.map((t, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <TestTube2 className="size-3 text-brand-600" />
                        <span>{t}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-6 border-t border-border pt-4">
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full justify-between"
                  asChild
                >
                  <Link to={`/tests?q=${encodeURIComponent(concern.slug)}`}>
                    <span>{isBn ? "টেস্ট সমূহ দেখুন" : "View Tests & Packages"}</span>
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
