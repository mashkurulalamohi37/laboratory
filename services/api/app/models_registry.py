"""Imports every ORM model so `Base.metadata` is complete (Alembic, tests)."""

from app.core.outbox import OutboxEvent
from app.modules.audit.models import AuditLog
from app.modules.auth.models import (
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    Session,
    User,
    UserRole,
)
from app.modules.billing.models import Invoice, InvoiceItem
from app.modules.booking.models import Booking, BookingItem, BookingStatusHistory
from app.modules.catalog.models import (
    Category,
    ConcernPackage,
    ConcernTest,
    Department,
    HealthConcern,
    Package,
    PackageTest,
    Preparation,
    PriceList,
    PriceListItem,
    ReferenceRange,
    SampleType,
    SearchSynonym,
    Test,
    TestParameter,
)
from app.modules.centre.models import Branch, Centre, CentreHours, Holiday, Lab
from app.modules.cms.models import Banner, Faq, Page
from app.modules.collection.models import CollectionAssignment, CollectionEvent, Collector
from app.modules.corporate.models import Corporate, CorporateContract, CorporateEmployee
from app.modules.coupon.models import Coupon, CouponRule, CouponUsage
from app.modules.crm.models import SupportTicket, TicketMessage
from app.modules.finance.models import ArApRecord, Expense
from app.modules.geo.models import Area, District, Division, Upazila
from app.modules.inventory.models import (
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    StockBatch,
    StockMovement,
)
from app.modules.lab.models import LabOrder, LabOrderItem
from app.modules.notification.models import NotificationLog, NotificationTemplate
from app.modules.partner.models import CommissionEntry, CommissionRule, Partner
from app.modules.patient.models import Address, FamilyLink, Patient
from app.modules.payment.models import Payment, PaymentCallback, PaymentTransaction
from app.modules.report.models import (
    Report,
    ReportShare,
    ReportSignature,
    ReportVerificationToken,
    ReportVersion,
)
from app.modules.result.models import CriticalAlert, Result, ResultComment, ResultParameter
from app.modules.sample.models import (
    Sample,
    SampleEvent,
    SampleRejectionReason,
    SampleTransfer,
    SampleTransferItem,
)
from app.modules.scheduling.models import SlotHold, SlotInstance, SlotTemplate

__all__ = [
    "Address",
    "ArApRecord",
    "Area",
    "AuditLog",
    "Banner",
    "Booking",
    "BookingItem",
    "BookingStatusHistory",
    "Branch",
    "Category",
    "Centre",
    "CentreHours",
    "CollectionAssignment",
    "CollectionEvent",
    "Collector",
    "CommissionEntry",
    "CommissionRule",
    "ConcernPackage",
    "ConcernTest",
    "Corporate",
    "CorporateContract",
    "CorporateEmployee",
    "Coupon",
    "CouponRule",
    "CouponUsage",
    "CriticalAlert",
    "Department",
    "District",
    "Division",
    "Expense",
    "FamilyLink",
    "Faq",
    "HealthConcern",
    "Holiday",
    "InventoryItem",
    "Invoice",
    "InvoiceItem",
    "Lab",
    "LabOrder",
    "LabOrderItem",
    "NotificationLog",
    "NotificationTemplate",
    "OutboxEvent",
    "Package",
    "PackageTest",
    "Page",
    "Partner",
    "Patient",
    "Payment",
    "PaymentCallback",
    "PaymentTransaction",
    "Permission",
    "Preparation",
    "PriceList",
    "PriceListItem",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "ReferenceRange",
    "RefreshToken",
    "Report",
    "ReportShare",
    "ReportSignature",
    "ReportVerificationToken",
    "ReportVersion",
    "Result",
    "ResultComment",
    "ResultParameter",
    "Role",
    "RolePermission",
    "Sample",
    "SampleEvent",
    "SampleRejectionReason",
    "SampleTransfer",
    "SampleTransferItem",
    "SampleType",
    "SearchSynonym",
    "Session",
    "SlotHold",
    "SlotInstance",
    "SlotTemplate",
    "StockBatch",
    "StockMovement",
    "SupportTicket",
    "Test",
    "TestParameter",
    "TicketMessage",
    "Upazila",
    "User",
    "UserRole",
]
