import { unwrapWithMeta, type AdminUser } from "@nirnoy/api-client";
import { requestIdOf, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { currentLocale, formatBDPhone, formatDateTime, useTranslation } from "@nirnoy/i18n";
import {
  Badge,
  Button,
  Card,
  DataTable,
  Field,
  Input,
  Pagination,
  Select,
  type Column,
} from "@nirnoy/ui";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import { CreateStaffDrawer } from "./CreateStaffDrawer";
import { STATUS_TONE } from "./status";
import { UserDrawer } from "./UserDrawer";

const PAGE_SIZE = 20;
type Status = "ACTIVE" | "SUSPENDED" | "DISABLED";

function useDebounced<T>(value: T, ms = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

export default function UsersPage() {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const errorMessage = useErrorMessage();
  const locale = currentLocale();
  // Filters live in the URL so views are shareable and survive reloads.
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const type = params.get("type") ?? "";
  const status = params.get("status") ?? "";
  const [search, setSearch] = useState(params.get("q") ?? "");
  const q = useDebounced(search.trim());
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const update = (patch: Record<string, string>) =>
    setParams((prev) => {
      const nextParams = new URLSearchParams(prev);
      Object.entries(patch).forEach(([k, v]) => (v ? nextParams.set(k, v) : nextParams.delete(k)));
      return nextParams;
    }, { replace: true });

  useEffect(() => {
    if (q !== (params.get("q") ?? "")) update({ q, page: "" });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync only when the debounced term changes
  }, [q]);

  const query = useQuery({
    queryKey: ["admin-users", { q, type, status, page }],
    queryFn: () =>
      unwrapWithMeta(
        api.GET("/api/v1/admin/users", {
          params: {
            query: {
              q: q || undefined,
              is_staff: type === "" ? undefined : type === "staff",
              status: (status || undefined) as Status | undefined,
              page,
              page_size: PAGE_SIZE,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });

  const columns = useMemo<Column<AdminUser>[]>(
    () => [
      {
        key: "name",
        header: t("users.name"),
        cell: (u) => (
          <div className="min-w-0">
            <p className="truncate font-medium">{u.full_name ?? t("users.unnamed")}</p>
            {u.email && <p className="truncate text-xs text-muted">{u.email}</p>}
          </div>
        ),
      },
      {
        key: "phone",
        header: t("users.phone"),
        cell: (u) => <span className="tabular-nums">{u.phone ? formatBDPhone(u.phone, locale) : "—"}</span>,
      },
      {
        key: "roles",
        header: t("users.roles"),
        cell: (u) => (
          <div className="flex flex-wrap gap-1">
            {(u.roles ?? []).map((r) => (
              <Badge key={r.id} tone={r.role === "PATIENT" ? "neutral" : "brand"}>
                {r.role.replaceAll("_", " ")}
              </Badge>
            ))}
          </div>
        ),
      },
      {
        key: "status",
        header: t("users.status"),
        cell: (u) => <Badge tone={STATUS_TONE[u.status] ?? "neutral"}>{t(`status.${u.status}`)}</Badge>,
      },
      {
        key: "last_login",
        header: t("users.lastLogin"),
        hideOnMobile: true,
        cell: (u) =>
          u.last_login_at ? formatDateTime(u.last_login_at, locale) : <span className="text-muted">{t("users.never")}</span>,
      },
    ],
    [t, locale],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("users.title")}</h1>
        <Button onClick={() => setCreating(true)}>
          <UserPlus aria-hidden="true" />
          {t("users.create")}
        </Button>
      </div>

      <Card>
        <div className="grid gap-3 border-b border-border p-4 sm:grid-cols-[1fr_auto_auto]">
          <Field label={t("users.search")} className="[&>label]:sr-only">
            <Input
              type="search"
              placeholder={t("users.search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Field>
          <Field label={t("users.filterType")} className="[&>label]:sr-only">
            <Select value={type} onChange={(e) => update({ type: e.target.value, page: "" })}>
              <option value="">{t("users.filterType")}: {t("users.all")}</option>
              <option value="staff">{t("users.staff")}</option>
              <option value="patient">{t("users.patients")}</option>
            </Select>
          </Field>
          <Field label={t("users.filterStatus")} className="[&>label]:sr-only">
            <Select value={status} onChange={(e) => update({ status: e.target.value, page: "" })}>
              <option value="">{t("users.filterStatus")}: {t("users.all")}</option>
              {(["ACTIVE", "SUSPENDED", "DISABLED"] as const).map((s) => (
                <option key={s} value={s}>
                  {t(`status.${s}`)}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <DataTable
          caption={t("users.title")}
          columns={columns}
          rows={query.data?.data}
          rowKey={(u) => u.id}
          isLoading={query.isPending}
          loadingLabel={t("common:loading")}
          error={
            query.isError
              ? {
                  title: `${t("users.loadError")}: ${errorMessage(query.error)}`,
                  requestId: requestIdOf(query.error),
                  onRetry: () => void query.refetch(),
                }
              : null
          }
          empty={{ title: t("users.emptyTitle"), description: t("users.emptyBody") }}
          onRowClick={(u) => setSelected(u.id)}
        />
        {query.data && (
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={query.data.meta.total ?? 0}
            onPageChange={(p) => update({ page: String(p) })}
            labels={{
              previous: t("common:previous"),
              next: t("common:next"),
              summary: (p, n) => t("common:pageOf", { page: p, pages: n }),
            }}
          />
        )}
      </Card>

      <CreateStaffDrawer open={creating} onOpenChange={setCreating} onCreated={setSelected} />
      <UserDrawer userId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
