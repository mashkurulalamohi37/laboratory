import { zodResolver } from "@hookform/resolvers/zod";
import { expectNoContent, unwrap, type SessionInfo } from "@nirnoy/api-client";
import { requestIdOf, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { currentLocale, formatBDPhone, formatDateTime, setLocale, useTranslation } from "@nirnoy/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ConfirmDialog,
  ErrorState,
  Field,
  Input,
  LoadingRows,
  PasswordInput,
  Select,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, HeartPulse, LogOut, MapPin, Monitor, Smartphone, Users } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

export default function AccountPage() {
  const { t } = useTranslation("account");
  const { me, signOut } = useAuth();
  const navigate = useNavigate();
  if (!me) return null;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            {me.full_name ? t("greeting", { name: me.full_name }) : t("greetingAnonymous")}
          </h1>
          {me.phone && (
            <p className="mt-1 text-sm text-muted tabular-nums">
              {formatBDPhone(me.phone, currentLocale())}
            </p>
          )}
        </div>
        <Button
          variant="secondary"
          onClick={async () => {
            await signOut();
            navigate("/", { replace: true });
          }}
        >
          <LogOut aria-hidden="true" />
          {t("common:signOut")}
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Link
          to="/account/bookings"
          className="flex flex-col items-center rounded-xl border border-border bg-subtle/50 p-4 text-center transition hover:border-brand hover:bg-subtle"
        >
          <Calendar className="mb-2 size-6 text-brand" />
          <span className="text-sm font-semibold text-foreground">My Bookings</span>
          <span className="text-xs text-muted">History & Reports</span>
        </Link>
        <Link
          to="/account/health-timeline"
          className="flex flex-col items-center rounded-xl border border-border bg-subtle/50 p-4 text-center transition hover:border-brand hover:bg-subtle"
        >
          <HeartPulse className="mb-2 size-6 text-brand" />
          <span className="text-sm font-semibold text-foreground">Health Trends</span>
          <span className="text-xs text-muted">Analyte History</span>
        </Link>
        <Link
          to="/account/family"
          className="flex flex-col items-center rounded-xl border border-border bg-subtle/50 p-4 text-center transition hover:border-brand hover:bg-subtle"
        >
          <Users className="mb-2 size-6 text-brand" />
          <span className="text-sm font-semibold text-foreground">Family</span>
          <span className="text-xs text-muted">Dependents</span>
        </Link>
        <Link
          to="/account/addresses"
          className="flex flex-col items-center rounded-xl border border-border bg-subtle/50 p-4 text-center transition hover:border-brand hover:bg-subtle"
        >
          <MapPin className="mb-2 size-6 text-brand" />
          <span className="text-sm font-semibold text-foreground">Addresses</span>
          <span className="text-xs text-muted">Home & Office</span>
        </Link>
        <Link
          to="/book"
          className="flex flex-col items-center rounded-xl border border-border bg-subtle/50 p-4 text-center transition hover:border-brand hover:bg-subtle"
        >
          <Smartphone className="mb-2 size-6 text-brand" />
          <span className="text-sm font-semibold text-foreground">Book Test</span>
          <span className="text-xs text-muted">Quick Schedule</span>
        </Link>
      </div>

      <ProfileCard />
      <PasswordCard hasPassword={me.has_password} />
      <SessionsCard />
    </div>
  );
}

function ProfileCard() {
  const { t } = useTranslation("account");
  const { api, me, reloadMe } = useAuth();
  const errorMessage = useErrorMessage();
  const form = useForm<{ full_name: string; preferred_language: "en" | "bn" }>({
    resolver: zodResolver(
      z.object({
        full_name: z.string().trim().min(2).max(150),
        preferred_language: z.enum(["en", "bn"]),
      }),
    ),
    values: {
      full_name: me?.full_name ?? "",
      preferred_language: me?.preferred_language === "bn" ? "bn" : "en",
    },
  });
  const save = useMutation({
    mutationFn: (body: { full_name: string; preferred_language: "en" | "bn" }) =>
      unwrap(api.PATCH("/api/v1/me", { body })),
    onSuccess: async (_, body) => {
      setLocale(body.preferred_language);
      await reloadMe();
      toast.success(t("common:saved"));
    },
  });

  return (
    <Card>
      <CardHeader title={t("profile")} />
      <CardBody>
        <form
          noValidate
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={form.handleSubmit((v) => save.mutate(v))}
        >
          <Field
            label={t("fullName")}
            hint={t("fullNameHint")}
            error={form.formState.errors.full_name?.message}
            className="sm:col-span-2"
          >
            <Input autoComplete="name" {...form.register("full_name")} />
          </Field>
          <Field label={t("preferredLanguage")}>
            <Select {...form.register("preferred_language")}>
              <option value="en">English</option>
              <option value="bn" lang="bn">বাংলা</option>
            </Select>
          </Field>
          {save.error && (
            <Alert tone="danger" className="sm:col-span-2">
              {errorMessage(save.error)}
            </Alert>
          )}
          <div className="sm:col-span-2">
            <Button type="submit" loading={save.isPending} disabled={!form.formState.isDirty}>
              {t("common:save")}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  );
}

function PasswordCard({ hasPassword }: { hasPassword: boolean }) {
  const { t } = useTranslation("account");
  const { api, reloadMe } = useAuth();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const schema = z.object({
    current_password: hasPassword ? z.string().min(1, t("auth:passwordRequired")) : z.string(),
    new_password: z
      .string()
      .min(10, t("auth:passwordHint"))
      .max(128)
      .regex(/[A-Za-z]/, t("auth:passwordHint"))
      .regex(/\d/, t("auth:passwordHint")),
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: "", new_password: "" },
  });
  const change = useMutation({
    mutationFn: (v: z.infer<typeof schema>) =>
      expectNoContent(
        api.POST("/api/v1/auth/password/change", {
          body: {
            current_password: hasPassword ? v.current_password : null,
            new_password: v.new_password,
          },
        }),
      ),
    onSuccess: async () => {
      form.reset();
      toast.success(t("passwordUpdated"));
      await reloadMe();
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  return (
    <Card>
      <CardHeader
        title={hasPassword ? t("changePassword") : t("setPassword")}
        description={hasPassword ? undefined : t("setPasswordBody")}
      />
      <CardBody>
        <form
          noValidate
          className="flex max-w-sm flex-col gap-4"
          onSubmit={form.handleSubmit((v) => change.mutate(v))}
        >
          {hasPassword && (
            <Field
              label={t("currentPassword")}
              error={form.formState.errors.current_password?.message}
            >
              <PasswordInput autoComplete="current-password" {...form.register("current_password")} />
            </Field>
          )}
          <Field
            label={t("newPassword")}
            hint={t("auth:passwordHint")}
            error={form.formState.errors.new_password?.message}
          >
            <PasswordInput autoComplete="new-password" {...form.register("new_password")} />
          </Field>
          {change.error && <Alert tone="danger">{errorMessage(change.error)}</Alert>}
          <Button type="submit" loading={change.isPending} className="self-start">
            {hasPassword ? t("changePassword") : t("setPassword")}
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

function deviceLabel(ua: string | null | undefined, fallback: string): string {
  if (!ua) return fallback;
  const os = /Android|iPhone|iPad|Windows|Mac OS|Linux/.exec(ua)?.[0] ?? "";
  const browser = /Edg|Chrome|Firefox|Safari/.exec(ua)?.[0]?.replace("Edg", "Edge") ?? "";
  return [browser, os].filter(Boolean).join(" · ") || fallback;
}

function SessionsCard() {
  const { t } = useTranslation("account");
  const { api, signOut } = useAuth();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [confirmAll, setConfirmAll] = useState(false);

  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/sessions")),
  });
  const revoke = useMutation({
    mutationFn: (id: string) =>
      expectNoContent(
        api.DELETE("/api/v1/auth/sessions/{session_id}", { params: { path: { session_id: id } } }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sessions"] }),
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Card>
      <CardHeader
        title={t("sessions")}
        action={
          <Button variant="secondary" size="sm" onClick={() => setConfirmAll(true)}>
            {t("signOutEverywhere")}
          </Button>
        }
      />
      <CardBody className="pt-3">
        {sessions.isPending ? (
          <LoadingRows rows={2} label={t("common:loading")} />
        ) : sessions.isError ? (
          <ErrorState
            title={errorMessage(sessions.error)}
            requestId={requestIdOf(sessions.error)}
            onRetry={() => void sessions.refetch()}
            retryLabel={t("common:retry")}
          />
        ) : (
          <ul className="divide-y divide-border">
            {sessions.data.map((s: SessionInfo) => {
              const Icon = /Android|iPhone|Mobile/.test(s.user_agent ?? "") ? Smartphone : Monitor;
              return (
                <li key={s.id} className="flex items-center gap-3 py-3">
                  <Icon className="size-5 shrink-0 text-muted" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {deviceLabel(s.user_agent, t("unknownDevice"))}
                      {s.current && (
                        <Badge tone="brand" className="ml-2">
                          {t("thisDevice")}
                        </Badge>
                      )}
                    </p>
                    <p className="text-xs text-muted">
                      {t("lastActive", { when: formatDateTime(s.last_seen_at, currentLocale()) })}
                    </p>
                  </div>
                  {!s.current && (
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={revoke.isPending && revoke.variables === s.id}
                      onClick={() => revoke.mutate(s.id)}
                    >
                      {t("signOutDevice")}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </CardBody>
      <ConfirmDialog
        open={confirmAll}
        onOpenChange={setConfirmAll}
        title={t("signOutEverywhere")}
        description={t("signOutEverywhereConfirm")}
        confirmLabel={t("signOutEverywhere")}
        cancelLabel={t("common:cancel")}
        destructive
        onConfirm={async () => {
          setConfirmAll(false);
          await signOut({ everywhere: true });
          navigate("/", { replace: true });
        }}
      />
    </Card>
  );
}
