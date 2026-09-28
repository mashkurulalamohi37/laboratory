# Phase 2 report: Catalog, Centres & Search

**Date:** 2026-09-27 · **Scope:** departments, categories, sample types, tests, parameters, reference ranges, packages, health concerns, price lists, centres, geo master, search with autocomplete & synonyms, CMS basics (banners, FAQs), public catalog web routes, and console catalog management.

## Completed

- **Database & Schemas:**
  - `geo`: divisions, districts, upazilas, areas, unions.
  - `catalog`: departments, categories, sample_types, tests, parameters, test_parameters, reference_ranges, packages, package_items, health_concerns, concern_items, price_lists, price_list_items.
  - `centre`: centres, centre_services, centre_working_hours.
  - `cms`: banners, pages, faqs.
  - `0002_catalog_centres_search` migration with full rollback support.
- **Reference Range Engine:**
  - Multi-dimensional matching on age range (days/years), sex (`M`/`F`/`ALL`), pregnancy status, and trimester.
  - Specificity scoring to resolve overlapping ranges safely.
  - Delta check thresholds (percentage and absolute) and panic/critical high/low values.
- **Search & Autocomplete:**
  - Postgres trigram + full-text search with phonetic synonym expansion.
  - Unified search results with type indicators (Test, Package, Department, Concern).
- **Public Patient Web (`apps/web`):**
  - Modern, responsive catalog browsing (`/tests`, `/tests/:slug`, `/packages`, `/packages/:slug`, `/concerns`, `/centres`, `/search`).
  - Hero with real-time debounced autocomplete search.
  - Detailed test pages with specimen requirements, fasting info, turnaround times, and parameters.
  - Package detail pages with bundled parameter breakdown and savings calculation.
  - Interactive centre locator with map links, open hours, and service badges.
- **Console Administration (`apps/console`):**
  - Catalog management (`/catalog`) for browsing and filtering active tests, parameters, and health packages.
- **Testing & Quality Gates:**
  - 100% test pass on catalog unit tests and reference range matcher test matrix.
  - Monorepo typecheck clean.
