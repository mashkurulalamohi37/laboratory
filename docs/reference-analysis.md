# Reference Analysis

**Reference:** lalpathlabsbd.com (inspected 2026-09-26, public pages only)
**Purpose:** Understand publicly visible functionality and information architecture. Nothing here is copied — no code, copy, assets, layout or branding. Our product uses an original identity (see `design-system.md`).

## 1. Method and limits

- Fetched public HTML for the homepage and 13 top-level routes, and extracted navigation, headings, form fields and link targets.
- The site is a Next.js app. Several pages (`/book-a-test`, `/nearest-center`, `/cart`, condition listings) render their lists client-side from an API we did not probe, so item-level detail (test fields, pricing display, slot selection) is **inferred, not observed**.
- We did not inspect authenticated areas, payment flows or back-office systems. Nothing about lab operations is publicly visible.

## 2. Public route inventory

| Route | Observed purpose |
|---|---|
| `/` | Home: test/package search, report download widget (lab no. + password), popular tests/packages, partner CTA, blog teaser, contact form (name, mobile, query) |
| `/test-and-package` | Catalog browse with three facets: **Condition**, **Lifestyle Disorder**, **Alphabet** |
| `/book-a-test` | Booking entry (client-rendered) |
| `/book-a-test/{condition-slug}` | Condition-filtered listing (≈37 condition slugs, e.g. diabetes, allergy, fever, disorders-of-kidney) |
| `/cart` | Cart (client-rendered) |
| `/download-report` | Report retrieval by **Lab Number + Password** (no account) |
| `/upload-prescription` | "Home collection query form": patient name, mobile, email, **OTP verify**, city dropdown, prescription attachment |
| `/nearest-center` | Centre locator (client-rendered) |
| `/our-labs` | Lab description and services offered |
| `/corporate-tie-up` | Corporate offerings: privilege discounts, pre-employment checkups, drug & hazardous testing, process description |
| `/partner-with-us` | Partner programme + "Become a Vendor" |
| `/promotion-and-discount` | Promotions listing |
| `/about-us` | Company, legacy, values |
| `/contact-us` | Corporate office, email, contact form |
| `/privacy-policy`, `/terms-of-use` | Legal |
| Blog | Links to an **external** parent-company blog |

**Header:** logo, phone hotline, search ("tests & packages"), cart. No visible login and no language switch.
**Footer groups:** Patients · Doctors · Business Partnership · About Us · Social.

## 3. User journeys (REFERENCE FUNCTIONALITY)

| Journey | How the reference handles it |
|---|---|
| Test discovery | Keyword search plus facets (condition / lifestyle / A–Z). Condition taxonomy is clinical and fine-grained. |
| Package discovery | Mixed into the same catalog as tests ("Tests & Packages"). |
| Booking | Add to cart → checkout (details not observable). No account needed. |
| Home collection | Mainly a **lead form** (upload-prescription page). Staff follow up offline. |
| Centre visit | Nearest-centre page. |
| Reports | Anonymous download with lab number + password printed on the receipt. |
| Prescription | Upload, then a callback. OTP verifies the phone. |
| Corporate | Brochure page with enquiry. No self-service portal. |
| Partner / vendor | Brochure page with enquiry. No portal. |
| Support | Contact form and hotline. |
| CMS-visible content | Banners, popular tests, promotions, about/legal pages and blog teaser, all evidently content-managed. |

## 4. OUR IMPROVEMENTS (summary — detail in `gap-analysis.md`)

1. **Accounts and family profiles.** Book for self or dependants, with a persistent history.
2. **Full online booking.** Slot selection, home or centre choice, coupons and online payment (bKash/Nagad/SSLCommerz).
3. **Live tracking.** Booking, collector and sample status timeline plus notifications.
4. **Reports in the portal.** Versioned PDFs, QR authenticity check, trends and a health timeline. Lab number + password stays as a guest fallback.
5. **Structured prescription workflow.** Upload → advisor review → quotation → one-tap confirm, instead of a lead form.
6. **Operational back office.** Collector app, sample chain of custody, LIS result entry, pathologist verification, inventory and finance. The reference exposes none of this publicly.
7. **Self-service corporate and partner portals**, replacing enquiry-only pages.
8. **Bangla + English**, BD address hierarchy (division → district → upazila/thana → area) and ৳ formatting.
9. **Health-concern taxonomy in plain language** for patients (e.g. "Sugar / Diabetes", "Thyroid"), mapped to the clinical conditions.
10. **First-party health articles** with SEO, instead of an external blog.
