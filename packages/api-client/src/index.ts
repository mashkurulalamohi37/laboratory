export {
  createApiClient,
  expectNoContent,
  unwrap,
  unwrapWithMeta,
  type ApiClient,
  type ApiClientOptions,
} from "./client";
export { ApiError, NETWORK_ERROR, type ErrorDetail } from "./errors";
export type { components, paths } from "./schema";
export { session, type AccessToken } from "./session";

import type { components } from "./schema";

type Schemas = components["schemas"];
export type Me = Schemas["MeResponse"];
export type TokenResponse = Schemas["TokenResponse"];
export type TwoFactorChallenge = Schemas["TwoFactorChallenge"];
export type SessionInfo = Schemas["SessionOut"];
export type AdminUser = Schemas["UserOut"];
export type RoleInfo = Schemas["RoleOut"];
export type PermissionInfo = Schemas["PermissionOut"];
export type AuditLogEntry = Schemas["AuditLogOut"];

// Catalogue (public)
export type Price = Schemas["Price"];
export type TestSummary = Schemas["TestSummary"];
export type TestDetail = Schemas["TestDetail"];
export type PackageSummary = Schemas["PackageSummary"];
export type PackageDetail = Schemas["PackageDetail"];
export type ConcernSummary = Schemas["ConcernSummary"];
export type ConcernDetail = Schemas["ConcernDetail"];
export type ConcernRef = Schemas["ConcernRef"];
export type CatalogFilters = Schemas["CatalogFilters"];
export type PreparationInfo = Schemas["PreparationOut"];
export type SearchResults = Schemas["SearchResults"];
export type Suggestion = Schemas["Suggestion"];
export type SitemapEntry = Schemas["SitemapEntry"];
export type CentreSummary = Schemas["CentreSummary"];
export type CentreDetail = Schemas["CentreDetail"];
export type OpeningHours = Schemas["HoursOut"];
export type GeoArea = Schemas["GeoOut"];
export type Banner = Schemas["BannerOut"];
export type CmsPage = Schemas["PageOut"];
export type Faq = Schemas["FaqOut"];

// Catalogue, centres and content (console)
export type AdminTestListItem = Schemas["AdminTestListItem"];
export type AdminTest = Schemas["AdminTestOut"];
export type AdminParameter = Schemas["ParameterOut"];
export type AdminReferenceRange = Schemas["ReferenceRangeOut"];
export type AdminPackageListItem = Schemas["AdminPackageListItem"];
export type AdminPackage = Schemas["AdminPackageOut"];
export type AdminConcern = Schemas["AdminConcernOut"];
export type AdminDepartment = Schemas["AdminDepartmentOut"];
export type AdminCategory = Schemas["AdminCategoryOut"];
export type AdminSampleType = Schemas["AdminSampleTypeOut"];
export type AdminPreparation = Schemas["AdminPreparationOut"];
export type Synonym = Schemas["SynonymOut"];
export type PriceList = Schemas["PriceListOut"];
export type PriceItem = Schemas["PriceItemOut"];
export type PriceHistory = Schemas["PriceHistoryOut"];
export type Branch = Schemas["BranchOut"];
export type Lab = Schemas["LabOut"];
export type AdminCentre = Schemas["AdminCentreOut"];
export type AdminHoliday = Schemas["AdminHolidayOut"];
export type AdminBanner = Schemas["AdminBannerOut"];
export type AdminPage = Schemas["AdminPageOut"];
export type AdminFaq = Schemas["AdminFaqOut"];

// Phase 8 & 9 Modules
export type InventoryItemOut = Schemas["InventoryItemOut"];
export type StockMovementOut = Schemas["StockMovementOut"];
export type LowStockAlertOut = Schemas["LowStockAlertOut"];
export type PurchaseOrderOut = Schemas["PurchaseOrderOut"];
export type ExpenseOut = Schemas["ExpenseOut"];
export type FinancialReconciliationOut = Schemas["FinancialReconciliationOut"];
export type ArApRecordOut = Schemas["ArApRecordOut"];
export type TicketOut = Schemas["TicketOut"];
export type TicketMessageOut = Schemas["TicketMessageOut"];
export type NotificationTemplateOut = Schemas["NotificationTemplateOut"];
export type NotificationLogOut = Schemas["NotificationLogOut"];
export type AnalyticsDashboardOut = Schemas["AnalyticsDashboardOut"];
export type TatMetricsOut = Schemas["TatMetricsOut"];
export type PatientHealthTimelineOut = Schemas["PatientHealthTimelineOut"];
export type AnalyteReading = Schemas["AnalyteReading"];
export type DepartmentWorkloadItem = Schemas["DepartmentWorkloadItem"];
