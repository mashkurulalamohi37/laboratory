import { FullPageSpinner, NotFoundPage, RequireAuth, RouteError } from "@nirnoy/app-core";
import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter } from "react-router";

import { Forbidden } from "./components/Forbidden";
import { Shell } from "./components/Shell";
import LoginPage from "./routes/LoginPage";

const DashboardPage = lazy(() => import("./routes/DashboardPage"));
const BookingsPage = lazy(() => import("./routes/BookingsPage"));
const CollectionsPage = lazy(() => import("./routes/CollectionsPage"));
const SamplesPage = lazy(() => import("./routes/SamplesPage"));
const LabWorklistPage = lazy(() => import("./routes/LabWorklistPage"));
const ReportsPage = lazy(() => import("./routes/ReportsPage"));
const InvoicesPage = lazy(() => import("./routes/InvoicesPage"));
const InventoryPage = lazy(() => import("./routes/InventoryPage"));
const FinancePage = lazy(() => import("./routes/FinancePage"));
const SupportCrmPage = lazy(() => import("./routes/SupportCrmPage"));
const CorporatePage = lazy(() => import("./routes/CorporatePage"));
const PartnerPage = lazy(() => import("./routes/PartnerPage"));
const CatalogPage = lazy(() => import("./routes/CatalogPage"));
const UsersPage = lazy(() => import("./routes/users/UsersPage"));
const RolesPage = lazy(() => import("./routes/RolesPage"));
const AuditLogPage = lazy(() => import("./routes/AuditLogPage"));

/** Lazy page, optionally gated by a permission (the API enforces it regardless). */
const page = (node: ReactNode, permission?: string) => (
  <RequireAuth permission={permission} forbidden={<Forbidden />}>
    <Suspense fallback={<FullPageSpinner />}>{node}</Suspense>
  </RequireAuth>
);

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage />, errorElement: <RouteError /> },
  {
    element: (
      <RequireAuth>
        <Shell />
      </RequireAuth>
    ),
    errorElement: <RouteError />,
    children: [
      { index: true, element: page(<DashboardPage />) },
      { path: "bookings", element: page(<BookingsPage />) },
      { path: "collections", element: page(<CollectionsPage />, "collection:view") },
      { path: "samples", element: page(<SamplesPage />, "sample:view") },
      { path: "lab", element: page(<LabWorklistPage />, "lab:view") },
      { path: "reports", element: page(<ReportsPage />) },
      { path: "billing", element: page(<InvoicesPage />) },
      { path: "inventory", element: page(<InventoryPage />, "inventory:view") },
      { path: "finance", element: page(<FinancePage />, "settings:manage") },
      { path: "crm", element: page(<SupportCrmPage />) },
      { path: "corporate", element: page(<CorporatePage />, "corporate:manage") },
      { path: "partners", element: page(<PartnerPage />, "partner:manage") },
      { path: "catalog", element: page(<CatalogPage />) },
      { path: "users", element: page(<UsersPage />, "user:manage") },
      { path: "roles", element: page(<RolesPage />, "role:manage") },
      { path: "audit", element: page(<AuditLogPage />, "audit:view") },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
