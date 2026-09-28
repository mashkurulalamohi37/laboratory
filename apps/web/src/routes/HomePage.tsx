import { useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Button, Card, cn, PriceTag } from "@nirnoy/ui";
import {
  Activity,
  ArrowRight,
  Award,
  CalendarCheck,
  Check,
  CheckCircle2,
  Clock,
  FileCheck2,
  HeartPulse,
  Home,
  Info,
  Microscope,
  Package,
  Plus,
  Search,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  TestTube2,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { SearchAutocomplete } from "../components/SearchAutocomplete";

const POPULAR_CONCERNS = [
  { slug: "diabetes", name: "Diabetes", name_bn: "ডায়াবেটিস", icon: Activity },
  { slug: "heart", name: "Heart Health", name_bn: "হার্ট ও হৃদরোগ", icon: HeartPulse },
  { slug: "thyroid", name: "Thyroid", name_bn: "থাইরয়েড", icon: Sparkles },
  { slug: "full-body", name: "Full Body Checkup", name_bn: "সম্পূর্ণ শরীর চেকআপ", icon: Package },
];

const FEATURED_TESTS = [
  {
    id: "cbc-demo-id",
    slug: "cbc",
    name: "Complete Blood Count (CBC)",
    name_bn: "কমপ্লিট ব্লাড কাউন্ট (সিবিসি)",
    department: "Hematology",
    tatHours: 6,
    preparation: "No fasting required",
    price: 60000, // ৳600
    mrp: 75000,
  },
  {
    id: "lipid-demo-id",
    slug: "lipid-profile",
    name: "Lipid Profile (Cholesterol)",
    name_bn: "লিপিড প্রোফাইল",
    department: "Biochemistry",
    tatHours: 12,
    preparation: "10-12 hours fasting required",
    price: 120000, // ৳1200
    mrp: 150000,
  },
  {
    id: "fbs-demo-id",
    slug: "fasting-blood-sugar",
    name: "Fasting Blood Sugar (FBS)",
    name_bn: "ফাস্টিং ব্লাড সুগার",
    department: "Biochemistry",
    tatHours: 4,
    preparation: "8-10 hours fasting required",
    price: 25000, // ৳250
    mrp: 30000,
  },
  {
    id: "hba1c-demo-id",
    slug: "hba1c",
    name: "HbA1c (3 Month Blood Sugar)",
    name_bn: "এইচবিএওয়ানসি (৩ মাসের গড় সুগার)",
    department: "Biochemistry",
    tatHours: 6,
    preparation: "No fasting required",
    price: 100000, // ৳1000
    mrp: 120000,
  },
];

const FEATURED_PACKAGES = [
  {
    id: "pkg-1",
    slug: "executive-health-package",
    name: "Executive Full Body Checkup",
    name_bn: "এক্সিকিউটিভ হেলথ চেকআপ প্যাকেজ",
    testCount: 42,
    price: 450000, // ৳4500
    mrp: 700000,
    savings: 250000,
    tags: ["Top Value", "Full Body"],
  },
  {
    id: "pkg-2",
    slug: "diabetes-care-package",
    name: "Diabetes Comprehensive Care",
    name_bn: "ডায়াবেটিস কেয়ার প্যাকেজ",
    testCount: 18,
    price: 220000, // ৳2200
    mrp: 350000,
    savings: 130000,
    tags: ["Diabetes"],
  },
];

const FAQS = [
  {
    q: "How does home sample collection work?",
    q_bn: "বাসায় এসে কীভাবে রক্ত বা স্যাম্পল সংগ্রহ করা হয়?",
    a: "Select your required tests, choose 'Home Sample Collection' at checkout, and select your preferred date & time slot. A trained phlebotomist visits your address with sterile barcoded vacutainer tubes.",
    a_bn: "আপনার প্রয়োজনীয় টেস্ট সিলেক্ট করে 'হোম স্যাম্পল কালেকশন' অপশনটি বেছে নিন। নির্ধারিত সময়ে আমাদের অভিজ্ঞ টেকনিশিয়ান আপনার বাসায় গিয়ে জীবাণুমুক্ত টিউবে স্যাম্পল সংগ্রহ করবেন।",
  },
  {
    q: "When will I get my digital test report?",
    q_bn: "রিপোর্ট কখন ও কীভাবে পাওয়া যাবে?",
    a: "Most routine tests (CBC, Blood Sugar, Lipid, LFT, KFT) are processed within 4-6 hours. You will receive an SMS and WhatsApp notification with a link to download your QR-verified PDF report.",
    a_bn: "অধিকাংশ টেস্টের রিপোর্ট ৪ থেকে ৬ ঘণ্টার মধ্যেই প্রস্তুত হয়ে যায়। রিপোর্ট প্রস্তুত হলে এসএমএস এবং হোয়াটসঅ্যাপের মাধ্যমে ভেরিফাইড পিডিএফ ডাউনলোড লিংক পৌঁছে যাবে।",
  },
  {
    q: "Are your diagnostic tests certified?",
    q_bn: "আপনাদের ল্যাব কি আন্তর্জাতিকভাবে অনুমোদিত?",
    a: "Yes, our central laboratories follow ISO 15189 international clinical laboratory quality standards, and every test report is reviewed and signed by qualified consultant pathologists.",
    a_bn: "হ্যাঁ, আমাদের সেন্ট্রাল ল্যাবরেটরি ISO 15189 আন্তর্জাতিক মানদণ্ড অনুসরণ করে এবং প্রতিটি রিপোর্ট সিনিয়র কনসালট্যান্ট প্যাথলজিস্ট দ্বারা স্বাক্ষরিত ও যাচাইকৃত।",
  },
];

const STEPS = [
  {
    icon: Search,
    title: "Choose your tests",
    title_bn: "টেস্ট বেছে নিন",
    body: "Search 100s of tests or pick a curated package with transparent pricing.",
    body_bn: "স্বচ্ছ মূল্যে টেস্ট বা প্যাকেজ খুঁজে বেছে নিন।",
  },
  {
    icon: CalendarCheck,
    title: "Book a time slot",
    title_bn: "সময় নির্ধারণ করুন",
    body: "Pick home collection or a nearby centre at a time that suits you.",
    body_bn: "বাসায় কালেকশন বা নিকটস্থ সেন্টার — আপনার সুবিধামতো সময়ে।",
  },
  {
    icon: FileCheck2,
    title: "Get verified reports",
    title_bn: "ভেরিফাইড রিপোর্ট পান",
    body: "Pathologist-signed, QR-verified PDF reports delivered to your phone.",
    body_bn: "প্যাথলজিস্ট স্বাক্ষরিত, কিউআর-ভেরিফাইড রিপোর্ট সরাসরি ফোনে।",
  },
];

const CONCERN_TONES = [
  "from-rose-500/15 to-rose-500/5 text-rose-600 dark:text-rose-400",
  "from-red-500/15 to-red-500/5 text-red-600 dark:text-red-400",
  "from-violet-500/15 to-violet-500/5 text-violet-600 dark:text-violet-400",
  "from-brand-500/20 to-brand-500/5 text-brand-600",
];

export default function HomePage() {
  const { i18n } = useTranslation();
  const { addItem, hasItem } = useCart();
  const isBn = i18n.language === "bn";

  const formatTk = (poisha: number) => `৳${Math.round(poisha / 100).toLocaleString()}`;

  return (
    <div className="flex flex-col gap-20 pb-20 sm:gap-24">
      {/* Hero */}
      <section className="relative isolate overflow-hidden border-b border-border/60">
        <div className="bg-dots absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" aria-hidden="true" />
        <div className="absolute -left-40 -top-40 -z-10 size-[520px] rounded-full bg-brand-300/30 blur-3xl dark:bg-brand-500/15" aria-hidden="true" />
        <div className="absolute -right-32 top-24 -z-10 size-[420px] rounded-full bg-accent-400/20 blur-3xl dark:bg-accent-500/10" aria-hidden="true" />

        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-14 sm:py-20 lg:grid-cols-[1.15fr_1fr] lg:py-24">
          <div className="flex animate-fade-up flex-col items-center text-center lg:items-start lg:text-left">
            <Badge tone="brand" className="mb-5 gap-1.5 px-3 py-1 text-xs shadow-[var(--shadow-card)]">
              <Sparkles className="size-3.5" />
              <span>{isBn ? "স্মার্ট ডিজিটাল ডায়াগনস্টিক প্ল্যাটফর্ম" : "Next-Gen Diagnostic Lab Platform"}</span>
            </Badge>

            <h1 className="max-w-2xl text-4xl font-extrabold leading-[1.1] tracking-tight text-fg sm:text-5xl lg:text-6xl">
              {isBn ? (
                <>
                  নির্ভুল ল্যাব টেস্ট ও স্বাস্থ্যসেবা, <span className="text-gradient">আপনার ঘরেই</span>
                </>
              ) : (
                <>
                  Accurate Lab Diagnostics <span className="text-gradient">Delivered To Your Doorstep</span>
                </>
              )}
            </h1>

            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
              {isBn
                ? "বাসায় বসে টেস্ট বুক করুন, সার্টিফাইড টেকনিশিয়ান দ্বারা স্যাম্পল দিন এবং কয়েক ঘণ্টার মধ্যে ডিজিটাল ভেরিফাইড রিপোর্ট পান।"
                : "Book diagnostic tests online, get sample collected at home by expert phlebotomists, and receive verified medical reports with QR verification."}
            </p>

            <div className="mt-8 flex w-full justify-center lg:justify-start">
              <SearchAutocomplete />
            </div>

            <div className="mt-6 flex max-w-xl flex-wrap items-center justify-center gap-2 lg:justify-start">
              <span className="mr-1 text-xs font-semibold uppercase tracking-wider text-muted">
                {isBn ? "জনপ্রিয়:" : "Popular:"}
              </span>
              {POPULAR_CONCERNS.map((c) => (
                <Link
                  key={c.slug}
                  to="/concerns"
                  className="group inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-fg shadow-[var(--shadow-card)] hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  <c.icon className="size-3.5 text-brand-600 transition-transform group-hover:scale-125" />
                  {isBn ? c.name_bn : c.name}
                </Link>
              ))}
            </div>

            <div className="mt-10 flex flex-wrap justify-center gap-x-8 gap-y-3 text-sm text-muted lg:justify-start">
              {[
                { icon: ShieldCheck, text: isBn ? "ISO 15189 মানসম্পন্ন" : "ISO 15189 compliant" },
                { icon: Clock, text: isBn ? "৪–৬ ঘণ্টায় রিপোর্ট" : "Reports in 4–6 hrs" },
                { icon: Home, text: isBn ? "ফ্রি হোম কালেকশন" : "Home collection" },
              ].map(({ icon: Icon, text }) => (
                <span key={text} className="inline-flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-full bg-success-bg text-success">
                    <Icon className="size-3.5" />
                  </span>
                  {text}
                </span>
              ))}
            </div>
          </div>

          {/* Hero visual: stacked preview cards */}
          <div className="relative mx-auto hidden h-[440px] w-full max-w-md lg:block" aria-hidden="true">
            <div className="absolute inset-6 rounded-[32px] bg-gradient-brand opacity-95 shadow-[var(--shadow-pop)]" />
            <div className="bg-dots absolute inset-6 rounded-[32px] opacity-30 [--brand-500:white]" />
            <div className="absolute inset-x-14 top-16 flex flex-col items-center text-center text-white">
              <div className="flex size-20 items-center justify-center rounded-3xl bg-white/15 ring-1 ring-white/25 backdrop-blur">
                <Microscope className="size-10" />
              </div>
              <p className="mt-5 font-display text-2xl font-bold">
                {isBn ? "আপনার স্বাস্থ্য, আমাদের অগ্রাধিকার" : "Your health, precisely measured"}
              </p>
              <p className="mt-2 text-sm text-white/80">
                {isBn ? "অভিজ্ঞ প্যাথলজিস্ট দ্বারা যাচাইকৃত" : "Reviewed by consultant pathologists"}
              </p>
            </div>

            <div className="glass absolute -left-6 bottom-24 flex animate-float items-center gap-3 rounded-2xl border border-border p-4 shadow-[var(--shadow-pop)]">
              <span className="flex size-11 items-center justify-center rounded-xl bg-success-bg text-success">
                <FileCheck2 className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-fg">{isBn ? "রিপোর্ট প্রস্তুত" : "Report ready"}</p>
                <p className="text-xs text-muted">CBC · {isBn ? "ভেরিফাইড" : "QR verified"}</p>
              </div>
            </div>

            <div className="glass absolute -right-4 top-10 flex animate-float items-center gap-3 rounded-2xl border border-border p-4 shadow-[var(--shadow-pop)] [animation-delay:-3s]">
              <span className="flex size-11 items-center justify-center rounded-xl bg-accent-50 text-accent-500">
                <Home className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-fg">{isBn ? "হোম কালেকশন" : "Home collection"}</p>
                <p className="text-xs text-muted">{isBn ? "আজ, সকাল ৮–১০টা" : "Today, 8–10 AM"}</p>
              </div>
            </div>

            <div className="glass absolute bottom-4 right-6 flex animate-float items-center gap-2 rounded-full border border-border px-4 py-2.5 shadow-[var(--shadow-pop)] [animation-delay:-1.5s]">
              <Clock className="size-4 text-brand-600" />
              <p className="text-sm font-semibold text-fg">{isBn ? "৪–৬ ঘণ্টায় ফলাফল" : "Results in 4–6 hrs"}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Value Pillars */}
      <section className="mx-auto w-full max-w-6xl px-4">
        <div className="grid gap-5 sm:grid-cols-3">
          {[
            {
              icon: Home,
              title: isBn ? "হোম স্যাম্পল কালেকশন" : "Home Sample Collection",
              body: isBn
                ? "আপনার সুবিধাজনক সময়ে দক্ষ টেকনিশিয়ান বাসায় এসে স্যাম্পল সংগ্রহ করবেন।"
                : "Hassle-free sample collection from your home by certified phlebotomists.",
            },
            {
              icon: Clock,
              title: isBn ? "দ্রুততম অনলাইন রিপোর্ট" : "Fastest Digital Reports",
              body: isBn
                ? "অধিকাংশ রুটিন টেস্টের রিপোর্ট মাত্র ৪–৬ ঘণ্টায় অনলাইনে পাওয়া যায়।"
                : "Get verified digital reports in 4-6 hours directly on your smartphone.",
            },
            {
              icon: Award,
              title: isBn ? "১০০% নির্ভুল ও ভেরিফাইড" : "100% Quality Assured",
              body: isBn
                ? "সিনিয়র প্যাথলজিস্ট দ্বারা স্বাক্ষরিত ও কিউআর কোড সিকিউরড রিপোর্ট।"
                : "ISO-standard automated testing verified by senior consultant pathologists.",
            },
          ].map(({ icon: Icon, title, body }) => (
            <Card key={title} interactive className="group relative overflow-hidden p-7">
              <div
                className="absolute -right-10 -top-10 size-32 rounded-full bg-brand-100/60 transition-transform duration-500 group-hover:scale-150 dark:bg-brand-500/10"
                aria-hidden="true"
              />
              <div className="relative mb-5 flex size-13 items-center justify-center rounded-2xl bg-gradient-brand text-white shadow-[var(--shadow-brand)] transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110">
                <Icon className="size-6" />
              </div>
              <h3 className="relative text-lg font-bold text-fg">{title}</h3>
              <p className="relative mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto w-full max-w-6xl px-4">
        <SectionHeading
          eyebrow={isBn ? "কীভাবে কাজ করে" : "How it works"}
          title={isBn ? "মাত্র ৩টি সহজ ধাপে" : "Three simple steps to better health"}
          centered
        />
        <ol className="relative grid gap-6 md:grid-cols-3">
          <div
            className="absolute left-[16%] right-[16%] top-8 hidden h-0.5 bg-[repeating-linear-gradient(90deg,var(--brand-300)_0_8px,transparent_8px_16px)] md:block"
            aria-hidden="true"
          />
          {STEPS.map((step, i) => (
            <li key={step.title} className="group relative flex flex-col items-center text-center">
              <div className="relative flex size-16 items-center justify-center rounded-2xl border border-border bg-surface text-brand-600 shadow-[var(--shadow-card)] transition-all duration-300 group-hover:-translate-y-1 group-hover:border-brand-300 group-hover:bg-gradient-brand group-hover:text-white group-hover:shadow-[var(--shadow-brand)]">
                <step.icon className="size-7" />
                <span className="absolute -right-2 -top-2 flex size-6 items-center justify-center rounded-full bg-accent-500 text-xs font-bold text-white ring-4 ring-bg">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-bold text-fg">{isBn ? step.title_bn : step.title}</h3>
              <p className="mt-2 max-w-xs text-sm leading-relaxed text-muted">{isBn ? step.body_bn : step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Featured Health Packages */}
      <section className="mx-auto w-full max-w-6xl px-4">
        <SectionHeading
          eyebrow={isBn ? "প্যাকেজ" : "Packages"}
          title={isBn ? "জনপ্রিয় স্বাস্থ্য প্যাকেজসমূহ" : "Popular Health Checkup Packages"}
          description={isBn ? "সম্পূর্ণ পরিবারের সুস্থতায় সাশ্রয়ী মূল্যে টেস্ট প্যাকেজ" : "Curated diagnostic checkups with maximum savings"}
          action={<ViewAll to="/packages" label={isBn ? "সব প্যাকেজ দেখুন" : "View All"} />}
        />

        <div className="grid gap-6 md:grid-cols-2">
          {FEATURED_PACKAGES.map((pkg, idx) => {
            const added = hasItem(pkg.id);
            return (
              <Card key={pkg.id} interactive className="group flex flex-col overflow-hidden">
                <div
                  className={cn(
                    "relative overflow-hidden p-6 text-white",
                    idx === 0 ? "bg-gradient-brand" : "bg-gradient-to-br from-brand-800 to-brand-950",
                  )}
                >
                  <div className="absolute -bottom-12 -right-8 size-40 rounded-full bg-white/10 transition-transform duration-500 group-hover:scale-125" aria-hidden="true" />
                  <div className="relative flex items-center justify-between gap-2">
                    <div className="flex flex-wrap gap-2">
                      {pkg.tags.map((t) => (
                        <span key={t} className="rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold ring-1 ring-white/25">
                          {t}
                        </span>
                      ))}
                    </div>
                    <span className="rounded-full bg-accent-500 px-2.5 py-1 text-xs font-bold text-white shadow-md">
                      {isBn ? `সাশ্রয় ${formatTk(pkg.savings)}` : `Save ${formatTk(pkg.savings)}`}
                    </span>
                  </div>
                  <h3 className="relative mt-4 text-2xl font-bold">
                    <Link to={`/packages/${pkg.slug}`} className="link-underline">
                      {isBn ? pkg.name_bn : pkg.name}
                    </Link>
                  </h3>
                  <p className="relative mt-2 flex items-center gap-1.5 text-sm text-white/85">
                    <CheckCircle2 className="size-4" />
                    {isBn ? `${pkg.testCount} টি ল্যাব প্যারামিটার অন্তর্ভুক্ত` : `Includes ${pkg.testCount} vital parameters`}
                  </p>
                </div>

                <div className="flex flex-1 items-center justify-between gap-4 p-6">
                  <PriceTag
                    size="lg"
                    amount={formatTk(pkg.price)}
                    mrp={formatTk(pkg.mrp)}
                    off={`${Math.round((pkg.savings / pkg.mrp) * 100)}% off`}
                  />
                  <Button
                    onClick={() =>
                      addItem({
                        id: pkg.id,
                        type: "PACKAGE",
                        name: isBn ? pkg.name_bn : pkg.name,
                        slug: pkg.slug,
                        price: pkg.price,
                        mrp: pkg.mrp,
                      })
                    }
                    variant={added ? "soft" : "primary"}
                  >
                    {added ? <Check /> : <ShoppingBag />}
                    {added ? (isBn ? "যোগ করা হয়েছে" : "Added") : isBn ? "বুক করুন" : "Book Package"}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Popular Diagnostic Tests */}
      <section className="mx-auto w-full max-w-6xl px-4">
        <SectionHeading
          eyebrow={isBn ? "টেস্ট" : "Tests"}
          title={isBn ? "প্রয়োজনীয় ল্যাব টেস্ট" : "Frequently Booked Tests"}
          description={isBn ? "সবচেয়ে বেশি প্রয়োজনীয় ডায়াগনস্টিক টেস্ট ও মূল্য তালিকা" : "Transparent pricing with preparation guidelines"}
          action={<ViewAll to="/tests" label={isBn ? "সব টেস্ট দেখুন" : "View All"} />}
        />

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURED_TESTS.map((test) => {
            const added = hasItem(test.id);
            return (
              <Card key={test.id} interactive className="group flex flex-col justify-between p-5">
                <div>
                  <div className="flex items-center justify-between">
                    <Badge tone="neutral">{test.department}</Badge>
                    <span className="flex size-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition-all duration-300 group-hover:rotate-12 group-hover:bg-gradient-brand group-hover:text-white">
                      <TestTube2 className="size-4" />
                    </span>
                  </div>
                  <Link to={`/tests/${test.slug}`} className="mt-4 block">
                    <h4 className="line-clamp-2 font-display text-base font-bold leading-snug text-fg transition-colors group-hover:text-brand-700">
                      {isBn ? test.name_bn : test.name}
                    </h4>
                  </Link>
                  <div className="mt-3 space-y-1.5 text-xs text-muted">
                    <p className="flex items-center gap-1.5">
                      <Clock className="size-3.5 text-brand-500" />
                      {isBn ? `রিপোর্ট ${test.tatHours} ঘণ্টায়` : `Report in ${test.tatHours} hrs`}
                    </p>
                    <p className="flex items-center gap-1.5">
                      <Info className="size-3.5 text-brand-500" />
                      <span className="line-clamp-1">{test.preparation}</span>
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex items-end justify-between border-t border-dashed border-border pt-4">
                  <PriceTag amount={formatTk(test.price)} mrp={formatTk(test.mrp)} />
                  <Button
                    size="sm"
                    variant={added ? "soft" : "primary"}
                    aria-label={added ? undefined : `Add ${test.name}`}
                    onClick={() =>
                      addItem({
                        id: test.id,
                        type: "TEST",
                        name: isBn ? test.name_bn : test.name,
                        slug: test.slug,
                        price: test.price,
                        mrp: test.mrp,
                        tatHours: test.tatHours,
                        preparation: test.preparation,
                      })
                    }
                  >
                    {added ? <Check /> : <Plus />}
                    {added ? (isBn ? "যোগ হয়েছে" : "Added") : isBn ? "যোগ করুন" : "Add"}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Browse by concern */}
      <section className="mx-auto w-full max-w-6xl px-4">
        <SectionHeading
          eyebrow={isBn ? "স্বাস্থ্য সমস্যা" : "Health concerns"}
          title={isBn ? "স্বাস্থ্য সমস্যা অনুযায়ী খুঁজুন" : "Browse by health concern"}
          action={<ViewAll to="/concerns" label={isBn ? "সব দেখুন" : "View All"} />}
        />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {POPULAR_CONCERNS.map((c, i) => (
            <Link
              key={c.slug}
              to="/concerns"
              className="group flex flex-col items-start gap-4 rounded-[var(--radius-lg)] border border-border bg-surface p-5 shadow-[var(--shadow-card)] hover-lift"
            >
              <span
                className={cn(
                  "flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br transition-transform duration-300 group-hover:scale-110",
                  CONCERN_TONES[i % CONCERN_TONES.length],
                )}
              >
                <c.icon className="size-6" />
              </span>
              <span className="flex w-full items-center justify-between gap-2 font-display font-bold text-fg">
                {isBn ? c.name_bn : c.name}
                <ArrowRight className="size-4 shrink-0 -translate-x-1 text-brand-600 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto w-full max-w-3xl px-4">
        <SectionHeading
          eyebrow="FAQ"
          title={isBn ? "সাধারণ জিজ্ঞাসা" : "Frequently Asked Questions"}
          centered
        />
        <div className="space-y-3">
          {FAQS.map((faq, idx) => (
            <details
              key={idx}
              open={idx === 0}
              className="group rounded-[var(--radius-lg)] border border-border bg-surface shadow-[var(--shadow-card)] transition-[border-color,box-shadow] hover:border-brand-300 hover:shadow-[var(--shadow-hover)] open:border-brand-300"
            >
              <summary className="flex list-none items-center justify-between gap-4 rounded-[var(--radius-lg)] p-5 font-semibold text-fg [&::-webkit-details-marker]:hidden">
                <span className="group-hover:text-brand-700">{isBn ? faq.q_bn : faq.q}</span>
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-muted text-muted transition-all duration-300 group-open:rotate-45 group-open:bg-brand-600 group-open:text-white group-hover:bg-brand-50 group-hover:text-brand-700 group-open:group-hover:bg-brand-700 group-open:group-hover:text-white">
                  <Plus className="size-4" />
                </span>
              </summary>
              <p className="animate-fade-in px-5 pb-5 text-sm leading-relaxed text-muted">{isBn ? faq.a_bn : faq.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* CTA banner */}
      <section className="mx-auto w-full max-w-6xl px-4">
        <div className="relative isolate overflow-hidden rounded-[var(--radius-xl)] bg-gradient-brand px-6 py-12 text-center text-white shadow-[var(--shadow-pop)] sm:px-12 sm:py-16">
          <div className="absolute -left-16 -top-16 -z-10 size-64 rounded-full bg-white/10 blur-2xl" aria-hidden="true" />
          <div className="absolute -bottom-24 -right-10 -z-10 size-80 rounded-full bg-accent-500/30 blur-3xl" aria-hidden="true" />
          <h2 className="mx-auto max-w-2xl text-3xl font-extrabold sm:text-4xl">
            {isBn ? "আজই আপনার স্বাস্থ্য পরীক্ষা বুক করুন" : "Book your health checkup today"}
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-white/85">
            {isBn
              ? "বাসায় বসেই স্যাম্পল দিন, রিপোর্ট পান ফোনে।"
              : "Sample collected at home, verified reports on your phone — in hours, not days."}
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="bg-none bg-white text-brand-700 shadow-lg hover:bg-white hover:brightness-100 hover:shadow-xl dark:text-brand-300">
              <Link to="/tests">
                {isBn ? "টেস্ট দেখুন" : "Browse tests"}
                <ArrowRight className="transition-transform group-hover/btn:translate-x-1" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="border-white/40 text-white hover:border-white hover:bg-white/10">
              <Link to="/packages">{isBn ? "প্যাকেজ দেখুন" : "View packages"}</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
  action,
  centered = false,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  action?: ReactNode;
  centered?: boolean;
}) {
  return (
    <div
      className={cn(
        "mb-10 flex flex-col gap-4",
        centered ? "items-center text-center" : "sm:flex-row sm:items-end sm:justify-between",
      )}
    >
      <div>
        <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-brand-600">
          <span className="h-px w-6 bg-brand-500" aria-hidden="true" />
          {eyebrow}
        </p>
        <h2 className="text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">{title}</h2>
        {description && <p className="mt-2 text-sm text-muted sm:text-base">{description}</p>}
      </div>
      {action}
    </div>
  );
}

function ViewAll({ to, label }: { to: string; label: string }) {
  return (
    <Button asChild variant="secondary" size="sm" className="self-start sm:self-auto">
      <Link to={to}>
        {label}
        <ArrowRight className="transition-transform group-hover/btn:translate-x-1" />
      </Link>
    </Button>
  );
}
