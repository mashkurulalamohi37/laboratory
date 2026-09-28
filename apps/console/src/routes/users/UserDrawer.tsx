import { unwrap, type AdminUser } from "@nirnoy/api-client";
import { requestIdOf, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { currentLocale, formatBDPhone, formatDateTime, useTranslation } from "@nirnoy/i18n";
import {
  Badge,
  Button,
  ConfirmDialog,
  Drawer,
  ErrorState,
  Field,
  Input,
  LoadingRows,
  Select,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { STATUS_TONE } from "./status";
import { useRoles } from "./useRoles";

type Status = "ACTIVE" | "SUSPENDED" | "DISABLED";

export function UserDrawer({ userId, onClose }: { userId: string | null; onClose: () => void }) {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const errorMessage = useErrorMessage();

  const user = useQuery({
    queryKey: ["admin-user", userId],
    enabled: userId !== null,
    queryFn: () =>
      unwrap(api.GET("/api/v1/admin/users/{user_id}", { params: { path: { user_id: userId! } } })),
  });

  return (
    <Drawer
      open={userId !== null}
      onOpenChange={(open) => !open && onClose()}
      title={user.data?.full_name ?? t("users.detailTitle")}
      closeLabel={t("common:close")}
    >
      {user.isPending ? (
        <LoadingRows rows={4} label={t("common:loading")} />
      ) : user.isError ? (
        <ErrorState
          title={errorMessage(user.error)}
          requestId={requestIdOf(user.error)}
          onRetry={() => void user.refetch()}
          retryLabel={t("common:retry")}
        />
      ) : (
        <UserDetail user={user.data} />
      )}
    </Drawer>
  );
}

function UserDetail({ user }: { user: AdminUser }) {
  const { t } = useTranslation("console");
  const { can, me } = useAuth();
  const locale = currentLocale();
  const isSelf = me?.id === user.id;

  return (
    <div className="flex flex-col gap-6">
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted">{t("users.phone")}</dt>
        <dd className="tabular-nums">{user.phone ? formatBDPhone(user.phone, locale) : "—"}</dd>
        <dt className="text-muted">{t("users.email")}</dt>
        <dd className="break-all">{user.email ?? "—"}</dd>
        <dt className="text-muted">{t("users.status")}</dt>
        <dd>
          <Badge tone={STATUS_TONE[user.status] ?? "neutral"}>{t(`status.${user.status}`)}</Badge>
        </dd>
        <dt className="text-muted">{t("users.lastLogin")}</dt>
        <dd>{user.last_login_at ? formatDateTime(user.last_login_at, locale) : t("users.never")}</dd>
      </dl>

      <RolesSection user={user} canManage={can("role:manage")} />
      {!isSelf && <StatusSection user={user} />}
    </div>
  );
}

function useUserMutation<TVars>(
  userId: string,
  fn: (vars: TVars) => Promise<AdminUser>,
  successMessage: string,
) {
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  return useMutation({
    mutationFn: fn,
    onSuccess: async (updated) => {
      queryClient.setQueryData(["admin-user", userId], updated);
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success(successMessage);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });
}

function RolesSection({ user, canManage }: { user: AdminUser; canManage: boolean }) {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const roles = useRoles();
  const [newRole, setNewRole] = useState("");
  const [revoking, setRevoking] = useState<{ id: string; role: string } | null>(null);
  const path = { params: { path: { user_id: user.id } } };

  const grant = useUserMutation(
    user.id,
    (role: string) =>
      unwrap(api.POST("/api/v1/admin/users/{user_id}/roles", { ...path, body: { role, scope_type: "GLOBAL" } })),
    t("users.roleGranted"),
  );
  const revoke = useUserMutation(
    user.id,
    (userRoleId: string) =>
      unwrap(
        api.DELETE("/api/v1/admin/users/{user_id}/roles/{user_role_id}", {
          params: { path: { user_id: user.id, user_role_id: userRoleId } },
        }),
      ),
    t("users.roleRevoked"),
  );

  const held = new Set((user.roles ?? []).map((r) => r.role));
  const grantable = (roles.data ?? []).filter((r) => !held.has(r.code));

  return (
    <section aria-labelledby="roles-heading" className="flex flex-col gap-3">
      <h3 id="roles-heading" className="font-semibold">
        {t("users.roles")}
      </h3>
      <ul className="divide-y divide-border rounded-[var(--radius-md)] border border-border">
        {(user.roles ?? []).map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
            <span>
              {r.role.replaceAll("_", " ")}
              <span className="ml-2 text-xs text-muted">
                {r.scope_type === "GLOBAL" ? t("users.scopeGlobal") : r.scope_type}
              </span>
            </span>
            {canManage && (
              <Button variant="ghost" size="sm" onClick={() => setRevoking({ id: r.id, role: r.role })}>
                {t("users.revoke")}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {canManage && (
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (newRole) grant.mutate(newRole, { onSuccess: () => setNewRole("") });
          }}
        >
          <Field label={t("users.grantRole")} className="flex-1">
            <Select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
              <option value="">—</option>
              {grantable.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.name}
                </option>
              ))}
            </Select>
          </Field>
          <Button type="submit" variant="secondary" disabled={!newRole} loading={grant.isPending}>
            {t("users.grant")}
          </Button>
        </form>
      )}
      <ConfirmDialog
        open={revoking !== null}
        onOpenChange={(open) => !open && setRevoking(null)}
        title={t("users.revokeConfirm", {
          role: revoking?.role.replaceAll("_", " ") ?? "",
          name: user.full_name ?? user.phone ?? "",
        })}
        confirmLabel={t("users.revoke")}
        cancelLabel={t("common:cancel")}
        destructive
        loading={revoke.isPending}
        onConfirm={() =>
          revoking && revoke.mutate(revoking.id, { onSettled: () => setRevoking(null) })
        }
      />
    </section>
  );
}

function StatusSection({ user }: { user: AdminUser }) {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const [target, setTarget] = useState<Status>(user.status as Status);
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);

  const change = useUserMutation(
    user.id,
    (body: { status: Status; reason: string }) =>
      unwrap(
        api.PATCH("/api/v1/admin/users/{user_id}/status", {
          params: { path: { user_id: user.id } },
          body,
        }),
      ),
    t("users.statusChanged"),
  );

  const destructive = target !== "ACTIVE";
  return (
    <section aria-labelledby="status-heading" className="flex flex-col gap-3">
      <h3 id="status-heading" className="font-semibold">
        {t("users.changeStatus")}
      </h3>
      <div className="grid gap-3 sm:grid-cols-[auto_1fr]">
        <Field label={t("users.status")}>
          <Select value={target} onChange={(e) => setTarget(e.target.value as Status)}>
            {(["ACTIVE", "SUSPENDED", "DISABLED"] as const).map((s) => (
              <option key={s} value={s}>
                {t(`status.${s}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("users.statusReason")}>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} />
        </Field>
      </div>
      <Button
        variant={destructive ? "danger" : "primary"}
        className="self-start"
        disabled={target === user.status || reason.trim().length < 3}
        onClick={() => setConfirming(true)}
      >
        {t("users.changeStatus")}
      </Button>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t("users.statusConfirmTitle", { status: t(`status.${target}`) })}
        description={destructive ? t("users.statusConfirmBody") : undefined}
        confirmLabel={t("common:confirm")}
        cancelLabel={t("common:cancel")}
        destructive={destructive}
        loading={change.isPending}
        confirmText={destructive ? (user.full_name ?? user.phone ?? undefined) : undefined}
        typeToConfirmLabel={t("users.typeName")}
        onConfirm={() =>
          change.mutate(
            { status: target, reason: reason.trim() },
            {
              onSettled: () => setConfirming(false),
              onSuccess: () => setReason(""),
            },
          )
        }
      />
    </section>
  );
}
