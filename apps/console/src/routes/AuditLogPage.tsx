import { unwrapWithMeta, type AuditLogEntry } from "@nirnoy/api-client";
import { requestIdOf, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { currentLocale, formatDateTime, useTranslation } from "@nirnoy/i18n";
import {
  Card,
  DataTable,
  Drawer,
  Field,
  Input,
  Pagination,
  type Column,
} from "@nirnoy/ui";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

const PAGE_SIZE = 50;

export default function AuditLogPage() {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const errorMessage = useErrorMessage();
  const locale = currentLocale();
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);

  const query = useQuery({
    queryKey: ["audit-logs", { page, action, entityType }],
    queryFn: () =>
      unwrapWithMeta(
        api.GET("/api/v1/admin/audit-logs", {
          params: {
            query: {
              page,
              page_size: PAGE_SIZE,
              action: action.trim() || undefined,
              entity_type: entityType.trim() || undefined,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });

  const columns = useMemo<Column<AuditLogEntry>[]>(
    () => [
      {
        key: "when",
        header: t("audit.when"),
        cell: (e) => <span className="whitespace-nowrap">{formatDateTime(e.at, locale)}</span>,
      },
      { key: "action", header: t("audit.action"), cell: (e) => <code className="text-xs">{e.action}</code> },
      {
        key: "entity",
        header: t("audit.entity"),
        cell: (e) => (
          <span className="text-xs">
            {e.entity_type}
            {e.entity_id && <span className="text-muted"> · {e.entity_id.slice(0, 8)}…</span>}
          </span>
        ),
      },
      {
        key: "actor",
        header: t("audit.actor"),
        hideOnMobile: true,
        cell: (e) =>
          e.actor_user_id ? (
            <span className="text-xs">
              {e.actor_user_id.slice(0, 8)}… {e.actor_roles.length > 0 && `(${e.actor_roles.join(", ")})`}
            </span>
          ) : (
            <span className="text-muted">{t("audit.system")}</span>
          ),
      },
      { key: "ip", header: t("audit.ip"), hideOnMobile: true, cell: (e) => e.ip ?? "—" },
    ],
    [t, locale],
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">{t("audit.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("audit.description")}</p>
      </div>
      <Card>
        <form
          className="grid gap-3 border-b border-border p-4 sm:grid-cols-2"
          onSubmit={(e) => e.preventDefault()}
        >
          <Field label={t("audit.filterAction")}>
            <Input
              placeholder="auth.login"
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
            />
          </Field>
          <Field label={t("audit.filterEntity")}>
            <Input
              placeholder="user"
              value={entityType}
              onChange={(e) => {
                setEntityType(e.target.value);
                setPage(1);
              }}
            />
          </Field>
        </form>
        <DataTable
          caption={t("audit.title")}
          columns={columns}
          rows={query.data?.data}
          rowKey={(e) => e.id}
          isLoading={query.isPending}
          loadingLabel={t("common:loading")}
          error={
            query.isError
              ? {
                  title: `${t("audit.loadError")}: ${errorMessage(query.error)}`,
                  requestId: requestIdOf(query.error),
                  onRetry: () => void query.refetch(),
                }
              : null
          }
          empty={{ title: t("audit.emptyTitle"), description: t("audit.emptyBody") }}
          onRowClick={setSelected}
        />
        {query.data && (
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={query.data.meta.total ?? 0}
            onPageChange={setPage}
            labels={{
              previous: t("common:previous"),
              next: t("common:next"),
              summary: (p, n) => t("common:pageOf", { page: p, pages: n }),
            }}
          />
        )}
      </Card>

      <Drawer
        open={selected !== null}
        onOpenChange={(open) => !open && setSelected(null)}
        title={t("audit.detail")}
        description={selected?.action}
        closeLabel={t("common:close")}
      >
        {selected && (
          <div className="flex flex-col gap-4 text-sm">
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
              <dt className="text-muted">{t("audit.when")}</dt>
              <dd>{formatDateTime(selected.at, locale)}</dd>
              <dt className="text-muted">{t("audit.entity")}</dt>
              <dd className="break-all">
                {selected.entity_type} {selected.entity_id}
              </dd>
              <dt className="text-muted">{t("audit.actor")}</dt>
              <dd className="break-all">{selected.actor_user_id ?? t("audit.system")}</dd>
              <dt className="text-muted">{t("audit.ip")}</dt>
              <dd>{selected.ip ?? "—"}</dd>
              <dt className="text-muted">{t("audit.requestId")}</dt>
              <dd className="break-all font-mono text-xs">{selected.request_id ?? "—"}</dd>
            </dl>
            {(["before", "after"] as const).map((k) =>
              selected[k] ? (
                <div key={k}>
                  <p className="mb-1 font-medium">{t(`audit.${k}`)}</p>
                  <pre className="overflow-x-auto rounded-[var(--radius-md)] bg-surface-muted p-3 text-xs">
                    {JSON.stringify(selected[k], null, 2)}
                  </pre>
                </div>
              ) : null,
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}
