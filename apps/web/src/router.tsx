import { FullPageSpinner, NotFoundPage, RequireAuth, RouteError } from "@nirnoy/app-core";
import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter } from "react-router";

import { Layout } from "./components/Layout";
import HomePage from "./routes/HomePage";

// Route-level code splitting
const LoginPage = lazy(() => import("./routes/LoginPage"));
const AccountPage = lazy(() => import("./routes/AccountPage"));
const BookingsHistoryPage = lazy(() => import("./routes/BookingsHistoryPage"));
const FamilyMembersPage = lazy(() => import("./routes/FamilyMembersPage"));
const AddressesPage = lazy(() => import("./routes/AddressesPage"));
const TestsPage = lazy(() => import("./routes/TestsPage"));
const TestDetailPage = lazy(() => import("./routes/TestDetailPage"));
const PackagesPage = lazy(() => import("./routes/PackagesPage"));
const PackageDetailPage = lazy(() => import("./routes/PackageDetailPage"));
const ConcernsPage = lazy(() => import("./routes/ConcernsPage"));
const CentresPage = lazy(() => import("./routes/CentresPage"));
const SearchPage = lazy(() => import("./routes/SearchPage"));
const BookingPage = lazy(() => import("./routes/BookingPage"));
const ReportVerificationPage = lazy(() => import("./routes/ReportVerificationPage"));
const HealthTimelinePage = lazy(() => import("./routes/HealthTimelinePage"));

const page = (node: ReactNode) => <Suspense fallback={<FullPageSpinner />}>{node}</Suspense>;

export const router = createBrowserRouter([
  {
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "login", element: page(<LoginPage />) },
      { path: "tests", element: page(<TestsPage />) },
      { path: "tests/:slug", element: page(<TestDetailPage />) },
      { path: "packages", element: page(<PackagesPage />) },
      { path: "packages/:slug", element: page(<PackageDetailPage />) },
      { path: "concerns", element: page(<ConcernsPage />) },
      { path: "centres", element: page(<CentresPage />) },
      { path: "search", element: page(<SearchPage />) },
      { path: "book", element: page(<BookingPage />) },
      { path: "verify/report/:token", element: page(<ReportVerificationPage />) },
      { path: "verify/reports/:token", element: page(<ReportVerificationPage />) },
      {
        path: "account",
        children: [
          {
            index: true,
            element: page(
              <RequireAuth>
                <AccountPage />
              </RequireAuth>,
            ),
          },
          {
            path: "bookings",
            element: page(
              <RequireAuth>
                <BookingsHistoryPage />
              </RequireAuth>,
            ),
          },
          {
            path: "family",
            element: page(
              <RequireAuth>
                <FamilyMembersPage />
              </RequireAuth>,
            ),
          },
          {
            path: "addresses",
            element: page(
              <RequireAuth>
                <AddressesPage />
              </RequireAuth>,
            ),
          },
          {
            path: "health-timeline",
            element: page(
              <RequireAuth>
                <HealthTimelinePage />
              </RequireAuth>,
            ),
          },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
