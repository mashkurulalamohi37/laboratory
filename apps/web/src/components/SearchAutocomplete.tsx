import { useEffect, useRef, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useTranslation } from "@nirnoy/i18n";
import { Badge } from "@nirnoy/ui";
import { Building2, HeartPulse, Package, Search, TestTube2, X } from "lucide-react";
import { useNavigate } from "react-router";
import { app } from "../api";

interface SuggestionItem {
  type: "TEST" | "PACKAGE" | "CONCERN" | "CENTRE";
  id: string;
  title: string;
  subtitle?: string;
  slug?: string;
}

export function SearchAutocomplete() {
  const { i18n } = useTranslation("catalog");
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [, setLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await unwrap(
          app.api.GET("/api/v1/search", {
            params: { query: { q: query.trim() } },
          }),
        );
        if (data) {
          const items: SuggestionItem[] = [];
          if (data.tests) {
            data.tests.forEach((test: any) => {
              items.push({
                type: "TEST",
                id: test.id,
                title: i18n.language === "bn" && test.name_bn ? test.name_bn : test.name,
                subtitle: test.department_name,
                slug: test.slug,
              });
            });
          }
          if (data.packages) {
            data.packages.forEach((pkg: any) => {
              items.push({
                type: "PACKAGE",
                id: pkg.id,
                title: i18n.language === "bn" && pkg.name_bn ? pkg.name_bn : pkg.name,
                subtitle: "Health Package",
                slug: pkg.slug,
              });
            });
          }
          if (data.concerns) {
            data.concerns.forEach((c: any) => {
              items.push({
                type: "CONCERN",
                id: c.id,
                title: i18n.language === "bn" && c.name_bn ? c.name_bn : c.name,
                subtitle: "Health Condition",
                slug: c.slug,
              });
            });
          }
          if (data.centres) {
            data.centres.forEach((centre: any) => {
              items.push({
                type: "CENTRE",
                id: centre.id,
                title: i18n.language === "bn" && centre.name_bn ? centre.name_bn : centre.name,
                subtitle: centre.address,
                slug: centre.id,
              });
            });
          }
          setSuggestions(items);
          setIsOpen(true);
        }
      } catch {
        // Fallback local search suggestions
        const q = query.toLowerCase();
        const demo: SuggestionItem[] = [
          { type: "TEST", id: "cbc", title: "Complete Blood Count (CBC)", subtitle: "Hematology", slug: "cbc" },
          { type: "TEST", id: "fbs", title: "Fasting Blood Sugar (FBS)", subtitle: "Biochemistry", slug: "fasting-blood-sugar" },
          { type: "TEST", id: "lipid", title: "Lipid Profile (Cholesterol)", subtitle: "Biochemistry", slug: "lipid-profile" },
          { type: "PACKAGE", id: "pkg-1", title: "Comprehensive Executive Health Checkup", subtitle: "Health Package", slug: "executive-health-package" },
          { type: "PACKAGE", id: "pkg-2", title: "Diabetes Care & Monitoring Package", subtitle: "Health Package", slug: "diabetes-care-package" },
          { type: "CONCERN", id: "c-diab", title: "Diabetes & Metabolism", subtitle: "Health Concern", slug: "diabetes" },
        ];
        const filtered = demo.filter((item) => item.title.toLowerCase().includes(q));
        setSuggestions(filtered);
        setIsOpen(true);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, i18n.language]);

  const handleSelect = (item: SuggestionItem) => {
    setIsOpen(false);
    setQuery("");
    if (item.type === "TEST") {
      navigate(`/tests/${item.slug || item.id}`);
    } else if (item.type === "PACKAGE") {
      navigate(`/packages/${item.slug || item.id}`);
    } else if (item.type === "CONCERN") {
      navigate(`/concerns`);
    } else if (item.type === "CENTRE") {
      navigate(`/centres`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && query.trim()) {
      setIsOpen(false);
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  const renderIcon = (type: SuggestionItem["type"]) => {
    switch (type) {
      case "TEST":
        return <TestTube2 className="size-4 text-brand-600" />;
      case "PACKAGE":
        return <Package className="size-4 text-emerald-600" />;
      case "CONCERN":
        return <HeartPulse className="size-4 text-rose-600" />;
      case "CENTRE":
        return <Building2 className="size-4 text-amber-600" />;
    }
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-2xl">
      <div className="group/search relative flex items-center">
        <Search className="pointer-events-none absolute left-5 size-5 text-muted transition-colors group-focus-within/search:text-brand-600" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search for blood tests, health packages, doctors or clinics..."
          className="h-14 w-full rounded-2xl border border-border bg-surface pl-13 pr-12 text-base text-fg shadow-[var(--shadow-hover)] transition-[border-color,box-shadow] duration-200 placeholder:text-muted/80 hover:border-brand-300 focus:border-brand-500 focus:outline-none focus:ring-[5px] focus:ring-brand-500/15 sm:h-16"
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setSuggestions([]);
              setIsOpen(false);
            }}
            aria-label="Clear search"
            className="absolute right-3 flex size-8 items-center justify-center rounded-full text-muted hover:bg-surface-muted hover:text-fg"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {isOpen && suggestions.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 max-h-96 overflow-y-auto animate-fade-in rounded-2xl border border-border bg-surface p-2 text-left shadow-[var(--shadow-pop)]">
          <div className="flex flex-col gap-0.5">
            {suggestions.map((item) => (
              <button
                key={`${item.type}-${item.id}`}
                type="button"
                onClick={() => handleSelect(item)}
                className="group flex w-full items-center justify-between rounded-xl px-4 py-3 text-left transition hover:bg-brand-50/70"
              >
                <div className="flex items-center gap-3">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-surface-muted transition-transform group-hover:scale-110 group-hover:bg-surface">
                    {renderIcon(item.type)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-fg group-hover:text-brand-700">{item.title}</p>
                    {item.subtitle && (
                      <p className="text-xs text-muted">{item.subtitle}</p>
                    )}
                  </div>
                </div>
                <Badge tone="neutral" className="text-[10px] uppercase font-bold tracking-wider">
                  {item.type}
                </Badge>
              </button>
            ))}
          </div>

          <div className="border-t border-border p-2 text-center">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                navigate(`/search?q=${encodeURIComponent(query.trim())}`);
              }}
              className="rounded-lg px-3 py-1.5 text-xs font-semibold text-brand-600 hover:bg-brand-50 hover:text-brand-700"
            >
              See all results for "{query}" →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
