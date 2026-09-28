import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import {
  Badge,
  Button,
  EmptyState,
  Input,
  LoadingRows,
  Modal,
  Select,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  Package,
  Plus,
  RefreshCw,
  Search,
  Truck,
} from "lucide-react";
import { useState } from "react";

export default function InventoryPage() {
  const { t } = useTranslation("console");
  const { api, can } = useAuth();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"items" | "alerts" | "orders">("items");
  const [searchQuery, setSearchQuery] = useState("");

  // Movement Modal
  const [movementModalOpen, setMovementModalOpen] = useState(false);
  const [movementItemId, setMovementItemId] = useState("");
  const [movementType, setMovementType] = useState<"IN" | "OUT" | "ADJUSTMENT" | "DISCARDED">("IN");
  const [movementQuantity, setMovementQuantity] = useState("10");
  const [movementReason, setMovementReason] = useState("");

  // Create PO Modal
  const [poModalOpen, setPoModalOpen] = useState(false);
  const [poSupplierName, setPoSupplierName] = useState("");
  const [poNotes, setPoNotes] = useState("");
  const [poItems, setPoItems] = useState<Array<{ item_id: string; quantity: number; unit_price: number }>>([]);

  // Queries
  const { data: items, isLoading: itemsLoading, refetch: refetchItems } = useQuery({
    queryKey: ["inventory", "items"],
    queryFn: () => unwrap(api.GET("/api/v1/inventory/items")),
  });

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ["inventory", "alerts"],
    queryFn: () => unwrap(api.GET("/api/v1/inventory/alerts")),
  });

  const { data: purchaseOrders, isLoading: poLoading } = useQuery({
    queryKey: ["inventory", "purchase-orders"],
    queryFn: () => unwrap(api.GET("/api/v1/inventory/purchase-orders")),
  });

  // Mutations
  const recordMovementMutation = useMutation({
    mutationFn: (body: { item_id: string; movement_type: string; quantity: number; reason?: string }) =>
      unwrap(
        api.POST("/api/v1/inventory/movements", {
          body,
        })
      ),
    onSuccess: () => {
      setMovementModalOpen(false);
      setMovementReason("");
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });

  const createPoMutation = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/inventory/purchase-orders", {
          body: {
            supplier_name: poSupplierName,
            notes: poNotes || undefined,
            items: poItems,
          },
        })
      ),
    onSuccess: () => {
      setPoModalOpen(false);
      setPoSupplierName("");
      setPoNotes("");
      setPoItems([]);
      void queryClient.invalidateQueries({ queryKey: ["inventory", "purchase-orders"] });
    },
  });

  const receivePoMutation = useMutation({
    mutationFn: (poId: string) =>
      unwrap(
        api.POST("/api/v1/inventory/purchase-orders/{po_id}/receive", {
          params: { path: { po_id: poId } },
        })
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });

  const filteredItems = (items ?? []).filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.name.toLowerCase().includes(q) ||
      item.code.toLowerCase().includes(q) ||
      (item.category && item.category.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-fg">{t("inventory.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("inventory.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          {can("inventory:update") && (
            <Button
              variant="secondary"
              onClick={() => {
                const first = items?.[0];
                if (first) setMovementItemId(first.id);
                setMovementModalOpen(true);
              }}
            >
              <Package className="size-4" />
              {t("inventory.recordMovement")}
            </Button>
          )}
          {can("purchase:manage") && (
            <Button
              variant="primary"
              onClick={() => {
                const first = items?.[0];
                if (first) {
                  setPoItems([{ item_id: first.id, quantity: 50, unit_price: 120000 }]);
                }
                setPoModalOpen(true);
              }}
            >
              <Plus className="size-4" />
              {t("inventory.createPo")}
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab("items")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
            activeTab === "items"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-muted hover:text-fg"
          }`}
        >
          <Boxes className="size-4" />
          Catalog Items & Stock ({items?.length ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("alerts")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
            activeTab === "alerts"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-muted hover:text-fg"
          }`}
        >
          <AlertTriangle className="size-4" />
          {t("inventory.lowStockAlerts")}
          {alerts && alerts.length > 0 && (
            <Badge tone="danger">{alerts.length}</Badge>
          )}
        </button>
        <button
          onClick={() => setActiveTab("orders")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
            activeTab === "orders"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-muted hover:text-fg"
          }`}
        >
          <Truck className="size-4" />
          Purchase Orders ({purchaseOrders?.length ?? 0})
        </button>
      </div>

      {/* TAB 1: Stock Items */}
      {activeTab === "items" && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-4">
            <div className="relative w-full max-w-sm">
              <Search className="absolute left-3 top-2.5 size-4 text-muted" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search reagents, consumables, or code..."
                className="pl-9"
              />
            </div>
            <button
              onClick={() => void refetchItems()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted hover:text-fg"
            >
              <RefreshCw className="size-3.5" />
              Refresh
            </button>
          </div>

          {itemsLoading ? (
            <LoadingRows rows={5} label="Loading inventory items..." />
          ) : filteredItems.length === 0 ? (
            <EmptyState
              icon={<Boxes className="size-8" />}
              title={t("inventory.empty")}
              description="No catalog inventory items have been created yet."
            />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">Item / Code</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Stock Level</th>
                    <th className="px-4 py-3">Reorder Point</th>
                    <th className="px-4 py-3">Unit</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredItems.map((item) => {
                    const isLow = item.current_stock <= item.reorder_level;
                    return (
                      <tr key={item.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                        <td className="px-4 py-3 font-medium text-fg">
                          <div>{item.name}</div>
                          <div className="text-xs text-muted font-mono">{item.code}</div>
                        </td>
                        <td className="px-4 py-3 text-muted">{item.category || "General"}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`font-semibold ${
                              isLow ? "text-red-600" : "text-fg"
                            }`}
                          >
                            {item.current_stock}
                          </span>
                          {isLow && (
                            <Badge tone="danger" className="ml-2">
                              LOW
                            </Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted">{item.reorder_level}</td>
                        <td className="px-4 py-3 text-muted">{item.unit_of_measure}</td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setMovementItemId(item.id);
                              setMovementModalOpen(true);
                            }}
                          >
                            Adjust
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Alerts */}
      {activeTab === "alerts" && (
        <div>
          {alertsLoading ? (
            <LoadingRows rows={3} label="Checking stock thresholds..." />
          ) : !alerts || alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center">
              <CheckCircle2 className="size-10 text-emerald-500" />
              <p className="mt-3 text-sm font-semibold text-fg">All Stock Levels Healthy</p>
              <p className="mt-1 text-xs text-muted">
                No items are currently below their safety threshold or nearing expiry.
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {alerts.map((alert) => (
                <div
                  key={alert.item_id}
                  className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50/50 p-4 text-red-950"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-red-100 p-2 text-red-700">
                      <AlertTriangle className="size-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{alert.item_name}</p>
                      <p className="text-xs text-red-800">
                        Code: <span className="font-mono">{alert.item_code}</span> · Current stock is{" "}
                        <strong className="text-red-900">{alert.current_stock}</strong> (Reorder point:{" "}
                        {alert.reorder_level})
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone="danger">Deficit: {alert.deficit}</Badge>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setMovementItemId(alert.item_id);
                        setMovementType("IN");
                        setMovementQuantity(String(alert.deficit * 2));
                        setMovementModalOpen(true);
                      }}
                    >
                      Receive Stock
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Purchase Orders */}
      {activeTab === "orders" && (
        <div className="flex flex-col gap-4">
          {poLoading ? (
            <LoadingRows rows={4} label="Loading purchase orders..." />
          ) : !purchaseOrders || purchaseOrders.length === 0 ? (
            <EmptyState
              icon={<Truck className="size-8" />}
              title="No Purchase Orders"
              description="Create a purchase order to initiate reagent procurement from approved vendors."
            />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">PO Number</th>
                    <th className="px-4 py-3">Supplier</th>
                    <th className="px-4 py-3">Total Amount</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {purchaseOrders.map((po) => {
                    const isDraft = po.status === "DRAFT";
                    const isReceived = po.status === "RECEIVED";
                    return (
                      <tr key={po.id} className="transition-colors duration-150 shadow-[inset_3px_0_0_transparent] hover:bg-brand-50/50 hover:shadow-[inset_3px_0_0_var(--brand-500)]">
                        <td className="px-4 py-3 font-mono font-medium text-fg">{po.po_number}</td>
                        <td className="px-4 py-3 text-fg">{po.supplier_name}</td>
                        <td className="px-4 py-3 font-semibold text-fg">
                          ৳{(po.total_amount / 100).toLocaleString("en-BD")}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            tone={isReceived ? "success" : isDraft ? "neutral" : "brand"}
                          >
                            {po.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {po.status === "SUBMITTED" && can("purchase:manage") && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => receivePoMutation.mutate(po.id)}
                              loading={receivePoMutation.isPending}
                            >
                              Receive Shipment
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Record Stock Movement Modal */}
      <Modal
        open={movementModalOpen}
        onOpenChange={setMovementModalOpen}
        title="Record Stock Movement"
      >
        <div className="flex flex-col gap-4 p-4">
          <div>
            <label className="text-xs font-medium text-muted">Target Item</label>
            <Select
              value={movementItemId}
              onChange={(e) => setMovementItemId(e.target.value)}
              className="mt-1"
            >
              {(items ?? []).map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.code}) - {i.current_stock} in stock
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted">Movement Type</label>
            <Select
              value={movementType}
              onChange={(e) => setMovementType(e.target.value as any)}
              className="mt-1"
            >
              <option value="IN">IN (Stock Received / Delivery)</option>
              <option value="OUT">OUT (Lab Usage / Test Runs)</option>
              <option value="ADJUSTMENT">ADJUSTMENT (Audit Reconciliation)</option>
              <option value="DISCARDED">DISCARDED (Damaged / Expired)</option>
            </Select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted">Quantity</label>
            <Input
              type="number"
              value={movementQuantity}
              onChange={(e) => setMovementQuantity(e.target.value)}
              min={1}
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted">Reason / Notes</label>
            <Input
              value={movementReason}
              onChange={(e) => setMovementReason(e.target.value)}
              placeholder="e.g. Monthly hematology analyzer restocking"
              className="mt-1"
            />
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setMovementModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() =>
                recordMovementMutation.mutate({
                  item_id: movementItemId,
                  movement_type: movementType,
                  quantity: Number(movementQuantity),
                  reason: movementReason || undefined,
                })
              }
              loading={recordMovementMutation.isPending}
            >
              Confirm Movement
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Purchase Order Modal */}
      <Modal
        open={poModalOpen}
        onOpenChange={setPoModalOpen}
        title="Create Procurement Purchase Order"
      >
        <div className="flex flex-col gap-4 p-4">
          <div>
            <label className="text-xs font-medium text-muted">Supplier Name</label>
            <Input
              value={poSupplierName}
              onChange={(e) => setPoSupplierName(e.target.value)}
              placeholder="e.g. BD Diagnostics Supply Ltd"
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted">Internal Notes</label>
            <Input
              value={poNotes}
              onChange={(e) => setPoNotes(e.target.value)}
              placeholder="Procurement notes or PO authorization reference"
              className="mt-1"
            />
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setPoModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!poSupplierName}
              onClick={() => createPoMutation.mutate()}
              loading={createPoMutation.isPending}
            >
              Submit Order
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
