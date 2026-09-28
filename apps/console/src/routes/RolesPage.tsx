import { unwrap, type RoleInfo } from "@nirnoy/api-client";
import { requestIdOf, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  Drawer,
  ErrorState,
  LoadingRows,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { useRoles } from "./users/useRoles";

export default function RolesPage() {
  const { t } = useTranslation("console");
  const errorMessage = useErrorMessage();
  const roles = useRoles();
  const [editing, setEditing] = useState<RoleInfo | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">{t("roles.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("roles.description")}</p>
      </div>
      <Card>
        {roles.isPending ? (
          <LoadingRows label={t("common:loading")} />
        ) : roles.isError ? (
          <ErrorState
            title={`${t("roles.loadError")}: ${errorMessage(roles.error)}`}
            requestId={requestIdOf(roles.error)}
            onRetry={() => void roles.refetch()}
            retryLabel={t("common:retry")}
          />
        ) : (
          <ul className="divide-y divide-border">
            {roles.data.map((role) => (
              <li key={role.code} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium">{role.name}</p>
                  <p className="text-xs text-muted">
                    <code>{role.code}</code> · {t("roles.count", { count: role.permissions.length })}
                  </p>
                </div>
                {role.code === "SUPER_ADMIN" ? (
                  <Badge tone="brand">{t("roles.immutable")}</Badge>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => setEditing(role)}>
                    {t("roles.edit")}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
      {editing && <PermissionEditor role={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function PermissionEditor({ role, onClose }: { role: RoleInfo; onClose: () => void }) {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState(() => new Set(role.permissions));

  const permissions = useQuery({
    queryKey: ["admin-permissions"],
    queryFn: () => unwrap(api.GET("/api/v1/admin/permissions")),
    staleTime: Infinity,
  });
  const grouped = useMemo(() => {
    const groups = new Map<string, string[]>();
    for (const p of permissions.data ?? []) {
      const [module = p.code] = p.code.split(":");
      groups.set(module, [...(groups.get(module) ?? []), p.code]);
    }
    return [...groups.entries()];
  }, [permissions.data]);

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        api.PUT("/api/v1/admin/roles/{role_code}/permissions", {
          params: { path: { role_code: role.code } },
          body: { permissions: [...selected].sort() },
        }),
      ),
    onSuccess: async () => {
      toast.success(t("roles.saved"));
      await queryClient.invalidateQueries({ queryKey: ["admin-roles"] });
      onClose();
    },
  });

  const toggle = (code: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });

  return (
    <Drawer
      open
      onOpenChange={(open) => !open && onClose()}
      title={`${t("roles.edit")}: ${role.name}`}
      description={t("roles.description")}
      closeLabel={t("common:close")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common:cancel")}
          </Button>
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            {t("common:save")}
          </Button>
        </>
      }
    >
      {permissions.isPending ? (
        <LoadingRows label={t("common:loading")} />
      ) : (
        <div className="flex flex-col gap-5">
          {save.error && <Alert tone="danger">{errorMessage(save.error)}</Alert>}
          {grouped.map(([module, codes]) => (
            <fieldset key={module} className="flex flex-col gap-2">
              <legend className="mb-1 text-sm font-semibold capitalize">{module}</legend>
              {codes.map((code) => (
                <label key={code} className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 accent-[var(--brand-600)]"
                    checked={selected.has(code)}
                    onChange={() => toggle(code)}
                  />
                  <code>{code}</code>
                </label>
              ))}
            </fieldset>
          ))}
        </div>
      )}
    </Drawer>
  );
}
