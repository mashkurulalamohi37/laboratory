# Clinical & Administrative Operations Manual

## 1. Executive Operations Overview

This operations manual governs day-to-day administration across all diagnostic centers, partner collection points, central processing laboratories, and administrative headquarters.

---

## 2. Staff Roles & Access Administration

The system enforces strict multi-tenant and multi-tier RBAC across all center operations:

| Role Code | Primary Responsibilities | Scope Constraints |
| :--- | :--- | :--- |
| `SUPER_ADMIN` | Global system configuration, tenant oversight, root audit | Global only |
| `PATHOLOGIST` | Laboratory result entry, critical alert sign-off, report release | Assigned Lab / Global |
| `LAB_TECHNICIAN` | Analyzer result entry, specimen processing, worklist management | Assigned Lab |
| `PHLEBOTOMIST` | Specimen collection, barcode accessioning, temperature logging | Assigned Branch / Field |
| `FINANCE_OFFICER`| Expense voucher approval, daily counter balancing, B2B AR/AP | Assigned Branch / Center |
| `INVENTORY_MNGR` | Reagent stock intake, batch expiry auditing, PO issuance | Assigned Center / Lab |
| `SUPPORT_AGENT`  | Patient inquiry resolution, ticket handling, rescheduling | Global / Center |

---

## 3. Critical Value Alert Response Protocol

When an entered test analyte breaches the defined critical reference limits (e.g., Blood Glucose < 2.5 mmol/L or > 25.0 mmol/L, Serum Potassium < 2.5 mmol/L or > 6.5 mmol/L):

1. **Automated Flagging:** Analyzer result automatically triggers a `CRITICAL_ALERT` with status `TRIGGERED`.
2. **Pathologist Alert:** Alert appears in red in the Console Dashboard banner and Lab Worklist.
3. **Immediate Clinical Contact:** Phlebotomy/Call Center lead must immediately place a direct phone call to the ordering clinician or patient.
4. **Audit Trail Sign-Off:** The staff member records the action taken (`action_taken`) and signs off the alert in the Console (`PATCH /api/v1/results/alerts/{id}/ack`).

---

## 4. Reagent Inventory & Batch Management

1. **Stock Movement Ledger:** All reagent deliveries, consumption, wastage, and manual audit adjustments must be logged via `/api/v1/inventory/movements`.
2. **Reorder Point Notifications:** When remaining units fall below `reorder_level`, an automated alert appears under `/inventory/alerts`.
3. **Purchase Order Lifecycle:**
   - Create procurement PO (`DRAFT`)
   - Approve and dispatch to vendor (`SUBMITTED`)
   - Acknowledge physical package delivery with lot/expiry verification (`RECEIVED`), automatically crediting active inventory.

---

## 5. Daily Financial Reconciliation Audit

At the conclusion of each day's operational hours (22:00 BST):

1. Cashier counters balance cash vaults, POS terminal receipts, and MFS merchant balances (bKash, Nagad).
2. Branch accountants run `/api/v1/finance/reconciliation?target_date=YYYY-MM-DD`.
3. System matches gross booking collections against recorded expense vouchers.
4. Discrepancies are reviewed and flagged as either `BALANCED` or requiring audit investigation.

---

## 6. Patient Support & CRM Escalation

- **SLA Deadlines:**
  - `URGENT` inquiries: 4 hours
  - `HIGH` priority inquiries: 12 hours
  - `NORMAL` inquiries: 48 hours
- **Message Threads:** Support staff communicate through the unified ticket thread (`/api/v1/crm/tickets/{id}/messages`).
- **Resolution:** A ticket may only be moved to `RESOLVED` after verifying patient satisfaction or resolving specimen queries.
