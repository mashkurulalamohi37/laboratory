import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useTranslation } from "@nirnoy/i18n";
import { Badge, Card } from "@nirnoy/ui";
import { Clock, MapPin, Phone } from "lucide-react";
import { app } from "../api";

export default function CentresPage() {
  const { i18n } = useTranslation("catalog");
  const isBn = i18n.language === "bn";

  const [centres, setCentres] = useState<any[]>([]);
  const [, setLoading] = useState(true);

  useEffect(() => {
    async function loadCentres() {
      setLoading(true);
      try {
        const data = await unwrap(app.api.GET("/api/v1/centres"));
        if (data) {
          setCentres(data);
        }
      } catch {
        // Fallback demo centres
        setCentres([
          {
            id: "dhanmondi-centre",
            code: "CTR-DMD",
            name: "Dhanmondi Central Diagnostic Centre & Lab",
            name_bn: "ধানমন্ডি সেন্ট্রাল ডায়াগনস্টিক সেন্টার ও ল্যাব",
            type: "BRANCH_CENTRE",
            address: "House 42, Road 7/A, Dhanmondi R/A, Dhaka 1209",
            phone: "+8801700000001",
            hours: "Daily 7:00 AM – 10:00 PM (Friday: 8:00 AM – 8:00 PM)",
            services: ["Sample Collection", "Clinical Pathology", "Biochemistry", "Microbiology"],
          },
          {
            id: "gulshan-centre",
            code: "CTR-GLS",
            name: "Gulshan-2 Premier Collection Centre",
            name_bn: "গুলশান-২ প্রিমিয়ার কালেকশন সেন্টার",
            type: "COLLECTION_POINT",
            address: "Plot 14, Road 113, Gulshan-2, Dhaka 1212",
            phone: "+8801700000002",
            hours: "Saturday – Thursday: 7:30 AM – 9:00 PM",
            services: ["Sample Collection", "Report Delivery", "Doctor Chamber"],
          },
          {
            id: "uttara-centre",
            code: "CTR-UTR",
            name: "Uttara Sector-7 Diagnostic Hub",
            name_bn: "উত্তরা সেক্টর-৭ ডায়াগনস্টিক হাব",
            type: "BRANCH_CENTRE",
            address: "House 18, Rabindra Sarani, Sector 7, Uttara, Dhaka",
            phone: "+8801700000003",
            hours: "Daily 7:00 AM – 10:00 PM",
            services: ["Sample Collection", "Automated Lab", "ECG", "Ultrasound"],
          },
          {
            id: "mirpur-centre",
            code: "CTR-MRP",
            name: "Mirpur-10 Regional Collection Point",
            name_bn: "মিরপুর-১০ আঞ্চলিক কালেকশন পয়েন্ট",
            type: "COLLECTION_POINT",
            address: "Mirpur 10 Roundabout, Section 10, Mirpur, Dhaka",
            phone: "+8801700000004",
            hours: "Saturday – Thursday: 8:00 AM – 8:00 PM",
            services: ["Sample Collection", "Fast Track Delivery"],
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    loadCentres();
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-10 max-w-3xl">
        <h1 className="text-3xl font-extrabold tracking-tight text-fg sm:text-4xl">
          {isBn ? "আমাদের ডায়াগনস্টিক ও কালেকশন সেন্টার" : "Our Lab Branches & Centres"}
        </h1>
        <p className="mt-2 text-base text-muted">
          {isBn
            ? "নিকটস্থ সেন্টারে গিয়ে সরাসরি স্যাম্পল দিন অথবা টেস্ট রিপোর্ট সংগ্রহ করুন।"
            : "Locate our certified diagnostic hubs, pathology laboratories, and sample collection points near you."}
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {centres.map((centre) => (
          <Card interactive
            key={centre.id}
            className="flex flex-col justify-between overflow-hidden rounded-3xl border border-border bg-surface p-6 sm:p-8 shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between">
                <Badge tone="brand" className="text-xs">
                  {centre.code || "CENTRE"}
                </Badge>
                <span className="rounded-full bg-surface-muted px-2.5 py-0.5 text-xs font-semibold text-muted">
                  {centre.type === "BRANCH_CENTRE" ? "Central Lab & Branch" : "Collection Point"}
                </span>
              </div>

              <h3 className="mt-4 text-xl font-bold text-fg">
                {isBn && centre.name_bn ? centre.name_bn : centre.name}
              </h3>

              <div className="mt-6 space-y-3 text-sm text-muted">
                <div className="flex items-start gap-3">
                  <MapPin className="size-5 text-brand-600 shrink-0 mt-0.5" />
                  <span>{centre.address || centre.address_line1 || "Dhaka, Bangladesh"}</span>
                </div>

                <div className="flex items-center gap-3">
                  <Phone className="size-5 text-brand-600 shrink-0" />
                  <a
                    href={`tel:${centre.phone || "+8801700000000"}`}
                    className="font-medium text-brand-700 hover:underline"
                  >
                    {centre.phone || "+8801700000000"}
                  </a>
                </div>

                <div className="flex items-start gap-3">
                  <Clock className="size-5 text-brand-600 shrink-0 mt-0.5" />
                  <span>{centre.hours || "Daily 7:00 AM – 10:00 PM"}</span>
                </div>
              </div>

              {centre.services && (
                <div className="mt-6 border-t border-border pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-muted mb-2">
                    Available Facilities
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {centre.services.map((srv: string, idx: number) => (
                      <span
                        key={idx}
                        className="rounded-lg bg-surface-muted border border-border/80 px-2.5 py-1 text-xs font-medium text-fg"
                      >
                        {srv}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
