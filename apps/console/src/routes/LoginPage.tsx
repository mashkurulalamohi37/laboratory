import { zodResolver } from "@hookform/resolvers/zod";
import { unwrap, type TwoFactorChallenge } from "@nirnoy/api-client";
import { LanguageSwitch, safeNextPath, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Alert, Button, Card, Field, Input, Logo, OtpInput, PasswordInput } from "@nirnoy/ui";
import { useMutation } from "@tanstack/react-query";
import { FileCheck2, FlaskConical, LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { z } from "zod";

export default function LoginPage() {
  const { t } = useTranslation("auth");
  const { status, sessionEnded } = useAuth();
  const [params] = useSearchParams();
  const next = safeNextPath(params.get("next"), "/");
  const [challenge, setChallenge] = useState<TwoFactorChallenge | null>(null);

  if (status === "authenticated") return <Navigate to={next} replace />;

  return (
    <div className="grid min-h-dvh bg-bg lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-gradient-brand p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="bg-dots absolute inset-0 opacity-40 [--brand-500:white]" aria-hidden="true" />
        <div className="absolute -right-24 -top-24 size-96 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
        <div className="absolute -bottom-32 -left-20 size-[28rem] rounded-full bg-accent-500/25 blur-3xl" aria-hidden="true" />
        <Logo label={t("console:title")} className="relative [&_span]:text-white" />
        <div className="relative max-w-md">
          <p className="font-display text-4xl font-extrabold leading-tight">
            Run the lab with confidence.
          </p>
          <p className="mt-4 text-lg text-white/80">
            Bookings, samples, results and reports — one secure workspace for every team.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-3">
            {[
              { icon: FlaskConical, label: "Lab" },
              { icon: FileCheck2, label: "Reports" },
              { icon: ShieldCheck, label: "2FA secured" },
            ].map(({ icon: Icon, label }) => (
              <div
                key={label}
                className="rounded-2xl bg-white/10 p-4 ring-1 ring-white/20 backdrop-blur transition-all hover:-translate-y-1 hover:bg-white/15"
              >
                <Icon className="size-5" />
                <p className="mt-3 text-sm font-semibold">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-sm text-white/60">© {new Date().getFullYear()} {t("console:title")}</p>
      </aside>

      <div className="relative flex flex-col items-center justify-center gap-6 px-4 py-10">
        <div className="bg-dots absolute inset-0 -z-0 [mask-image:radial-gradient(ellipse_at_center,black_10%,transparent_65%)] lg:hidden" aria-hidden="true" />
        <Logo label={t("console:title")} className="relative lg:hidden" />
        <Card className="relative w-full max-w-md animate-fade-up p-6 shadow-[var(--shadow-pop)] sm:p-9">
          {challenge ? (
            <TwoFactorStep challenge={challenge} next={next} onBack={() => setChallenge(null)} />
          ) : (
            <>
              <span className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                <LockKeyhole className="size-6" />
              </span>
              <h1 className="text-2xl font-extrabold tracking-tight">{t("staffTitle")}</h1>
              <p className="mt-1.5 text-sm text-muted">{t("staffBody")}</p>
              {sessionEnded && (
                <Alert tone="warning" className="mt-4">
                  {t("sessionExpired")}
                </Alert>
              )}
              <PasswordStep onChallenge={setChallenge} next={next} />
            </>
          )}
        </Card>
        <LanguageSwitch className="relative" />
      </div>
    </div>
  );
}

function PasswordStep({
  onChallenge,
  next,
}: {
  onChallenge: (c: TwoFactorChallenge) => void;
  next: string;
}) {
  const { t } = useTranslation("auth");
  const { api, completeSignIn } = useAuth();
  const errorMessage = useErrorMessage();
  const navigate = useNavigate();
  const form = useForm<{ identifier: string; password: string }>({
    resolver: zodResolver(
      z.object({
        identifier: z.string().trim().min(3, t("phoneInvalid")),
        password: z.string().min(1, t("passwordRequired")),
      }),
    ),
    defaultValues: { identifier: "", password: "" },
  });

  const login = useMutation({
    mutationFn: (v: { identifier: string; password: string }) =>
      unwrap(api.POST("/api/v1/auth/login", { body: { ...v, client: "web" } })),
    onSuccess: async (result) => {
      if ("challenge_id" in result) {
        onChallenge(result);
        return;
      }
      // Only when staff 2FA is disabled by configuration.
      await completeSignIn(result);
      navigate(next, { replace: true });
    },
  });

  return (
    <form noValidate className="mt-6 flex flex-col gap-4" onSubmit={form.handleSubmit((v) => login.mutate(v))}>
      <Field label={t("identifierLabel")} error={form.formState.errors.identifier?.message} required>
        <Input autoComplete="username" {...form.register("identifier")} />
      </Field>
      <Field label={t("passwordLabel")} error={form.formState.errors.password?.message} required>
        <PasswordInput autoComplete="current-password" {...form.register("password")} />
      </Field>
      {login.error && <Alert tone="danger">{errorMessage(login.error)}</Alert>}
      <Button type="submit" size="lg" block loading={login.isPending}>
        {t("common:continue")}
      </Button>
    </form>
  );
}

function TwoFactorStep({
  challenge,
  next,
  onBack,
}: {
  challenge: TwoFactorChallenge;
  next: string;
  onBack: () => void;
}) {
  const { t } = useTranslation("auth");
  const { api, completeSignIn } = useAuth();
  const errorMessage = useErrorMessage();
  const navigate = useNavigate();
  const form = useForm<{ code: string }>({
    resolver: zodResolver(z.object({ code: z.string().regex(/^\d{6}$/, t("codeInvalid")) })),
    defaultValues: { code: "" },
  });
  useEffect(() => form.setFocus("code"), [form]);

  const verify = useMutation({
    mutationFn: async (code: string) => {
      const token = await unwrap(
        api.POST("/api/v1/auth/2fa/verify", {
          body: { challenge_id: challenge.challenge_id, code, client: "web" },
        }),
      );
      await completeSignIn(token);
    },
    onSuccess: () => navigate(next, { replace: true }),
  });

  return (
    <form noValidate className="flex flex-col gap-4" onSubmit={form.handleSubmit(({ code }) => verify.mutate(code))}>
      <div>
        <span className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
          <ShieldCheck className="size-6" />
        </span>
        <h1 className="text-2xl font-extrabold tracking-tight">{t("twoFactorTitle")}</h1>
        <p className="mt-1 text-sm text-muted" aria-live="polite">
          {t("twoFactorBody", { phone: challenge.phone_hint })}
        </p>
      </div>
      <Field label={t("codeLabel")} error={form.formState.errors.code?.message} required>
        <OtpInput {...form.register("code")} />
      </Field>
      {verify.error && <Alert tone="danger">{errorMessage(verify.error)}</Alert>}
      <Button type="submit" size="lg" block loading={verify.isPending}>
        {t("verify")}
      </Button>
      <Button variant="link" onClick={onBack}>
        {t("common:back")}
      </Button>
    </form>
  );
}
