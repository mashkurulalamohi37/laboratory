import { zodResolver } from "@hookform/resolvers/zod";
import { unwrap } from "@nirnoy/api-client";
import { safeNextPath, useAuth, useErrorMessage } from "@nirnoy/app-core";
import { currentLocale, formatBDPhone, normalizeBDPhone, useTranslation } from "@nirnoy/i18n";
import { Alert, Button, Field, Input, OtpInput, PasswordInput, PhoneInput } from "@nirnoy/ui";
import { FileCheck2, HeartPulse, Home, KeyRound, MessageSquareText, ShieldCheck } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { z } from "zod";

const RESEND_SECONDS = 60;

export default function LoginPage() {
  const { t, i18n } = useTranslation("auth");
  const isBn = i18n.language === "bn";
  const { status, sessionEnded } = useAuth();
  const [params] = useSearchParams();
  const next = safeNextPath(params.get("next"), "/account");
  const [mode, setMode] = useState<"otp" | "password">("otp");

  if (status === "authenticated") return <Navigate to={next} replace />;

  return (
    <div className="relative isolate px-4 py-10 sm:py-16">
      <div className="bg-dots absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" aria-hidden="true" />
      <div className="mx-auto grid max-w-4xl animate-fade-up overflow-hidden rounded-[var(--radius-xl)] border border-border bg-surface shadow-[var(--shadow-pop)] md:grid-cols-[1fr_1.1fr]">
        <aside className="relative hidden overflow-hidden bg-gradient-brand p-10 text-white md:flex md:flex-col md:justify-between">
          <div className="absolute -right-20 -top-20 size-64 rounded-full bg-white/10 blur-2xl" aria-hidden="true" />
          <div className="absolute -bottom-24 -left-10 size-72 rounded-full bg-accent-500/25 blur-3xl" aria-hidden="true" />
          <div className="relative">
            <span className="flex size-14 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25 backdrop-blur">
              <HeartPulse className="size-7" />
            </span>
            <p className="mt-6 font-display text-3xl font-extrabold leading-tight">
              {isBn ? "আপনার স্বাস্থ্য, এক জায়গায়" : "Your health, all in one place"}
            </p>
            <p className="mt-3 text-white/85">
              {isBn
                ? "টেস্ট বুক করুন, স্যাম্পল ট্র্যাক করুন এবং রিপোর্ট ডাউনলোড করুন।"
                : "Book tests, track your samples and download reports anytime."}
            </p>
          </div>
          <ul className="relative mt-10 space-y-3 text-sm">
            {[
              { icon: Home, text: isBn ? "হোম স্যাম্পল কালেকশন" : "Home sample collection" },
              { icon: FileCheck2, text: isBn ? "কিউআর-ভেরিফাইড ডিজিটাল রিপোর্ট" : "QR-verified digital reports" },
              { icon: ShieldCheck, text: isBn ? "আপনার তথ্য সুরক্ষিত" : "Your data stays private" },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <span className="flex size-8 items-center justify-center rounded-lg bg-white/15">
                  <Icon className="size-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </aside>

        <div className="p-6 sm:p-10">
          <h1 className="text-2xl font-extrabold tracking-tight">{t("welcomeTitle")}</h1>
          <p className="mt-2 text-sm text-muted">{t("welcomeBody")}</p>
          {sessionEnded && (
            <Alert tone="warning" className="mt-4">
              {t("sessionExpired")}
            </Alert>
          )}
          <div className="mt-7">
            {mode === "otp" ? <OtpLogin next={next} /> : <PasswordLogin next={next} />}
          </div>
          <div className="mt-6 flex items-center gap-3 text-xs text-muted" aria-hidden="true">
            <span className="h-px flex-1 bg-border" />
            {"•"}
            <span className="h-px flex-1 bg-border" />
          </div>
          <Button
            variant="ghost"
            block
            className="mt-4 text-brand-700"
            onClick={() => setMode(mode === "otp" ? "password" : "otp")}
          >
            {mode === "otp" ? <KeyRound /> : <MessageSquareText />}
            {mode === "otp" ? t("usePassword") : t("useCode")}
          </Button>
        </div>
      </div>
    </div>
  );
}

function OtpLogin({ next }: { next: string }) {
  const { t } = useTranslation("auth");
  const { api, completeSignIn } = useAuth();
  const errorMessage = useErrorMessage();
  const navigate = useNavigate();
  const [phone, setPhone] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => window.clearTimeout(id);
  }, [cooldown]);

  const phoneForm = useForm<{ phone: string }>({
    resolver: zodResolver(
      z.object({ phone: z.string().refine((v) => normalizeBDPhone(v) !== null, t("phoneInvalid")) }),
    ),
    defaultValues: { phone: "" },
  });
  const codeForm = useForm<{ code: string }>({
    resolver: zodResolver(z.object({ code: z.string().regex(/^\d{6}$/, t("codeInvalid")) })),
    defaultValues: { code: "" },
  });

  // Move focus to the code field when that step appears (announced by screen readers).
  useEffect(() => {
    if (phone !== null) codeForm.setFocus("code");
  }, [phone, codeForm]);

  const send = useMutation({
    mutationFn: (value: string) =>
      unwrap(api.POST("/api/v1/auth/send-otp", { body: { phone: value, purpose: "LOGIN" } })),
    onSuccess: (data, value) => {
      setPhone(value);
      setCooldown(data.resend_after ?? RESEND_SECONDS);
      codeForm.reset({ code: "" });
    },
  });

  const verify = useMutation({
    mutationFn: async (code: string) => {
      const token = await unwrap(
        api.POST("/api/v1/auth/verify-otp", { body: { phone: phone!, code, client: "web" } }),
      );
      await completeSignIn(token);
    },
    onSuccess: () => navigate(next, { replace: true }),
  });

  if (phone === null) {
    return (
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={phoneForm.handleSubmit(({ phone: raw }) => send.mutate(normalizeBDPhone(raw)!))}
      >
        <Field
          label={t("phoneLabel")}
          hint={t("phoneHint")}
          error={phoneForm.formState.errors.phone?.message}
          required
        >
          <PhoneInput {...phoneForm.register("phone")} />
        </Field>
        {send.error && <Alert tone="danger">{errorMessage(send.error)}</Alert>}
        <Button type="submit" size="lg" block loading={send.isPending}>
          {t("sendCode")}
        </Button>
      </form>
    );
  }

  return (
    <form
      noValidate
      className="flex flex-col gap-4"
      onSubmit={codeForm.handleSubmit(({ code }) => verify.mutate(code))}
    >
      <p className="text-sm text-fg" aria-live="polite">
        {t("codeSentTo", { phone: formatBDPhone(phone, currentLocale()) })}
      </p>
      <Field label={t("codeLabel")} error={codeForm.formState.errors.code?.message} required>
        <OtpInput {...codeForm.register("code")} />
      </Field>
      {(verify.error || send.error) && (
        <Alert tone="danger">{errorMessage(verify.error ?? send.error)}</Alert>
      )}
      <Button type="submit" size="lg" block loading={verify.isPending}>
        {t("verify")}
      </Button>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <Button variant="link" onClick={() => { setPhone(null); send.reset(); verify.reset(); }}>
          {t("changeNumber")}
        </Button>
        {cooldown > 0 ? (
          <span className="text-muted" aria-live="polite">
            {t("resendIn", { seconds: cooldown })}
          </span>
        ) : (
          <Button variant="link" onClick={() => send.mutate(phone)} disabled={send.isPending}>
            {t("resend")}
          </Button>
        )}
      </div>
    </form>
  );
}

function PasswordLogin({ next }: { next: string }) {
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
    mutationFn: async (values: { identifier: string; password: string }) => {
      const result = await unwrap(
        api.POST("/api/v1/auth/login", { body: { ...values, client: "web" } }),
      );
      if ("challenge_id" in result) {
        // Staff accounts belong in the console, not the patient site.
        throw Object.assign(new Error(t("errors.STAFF_PASSWORD_LOGIN_REQUIRED")), {
          staff: true,
        });
      }
      await completeSignIn(result);
    },
    onSuccess: () => navigate(next, { replace: true }),
  });

  const loginError =
    login.error && "staff" in login.error ? login.error.message : login.error && errorMessage(login.error);

  return (
    <form noValidate className="flex flex-col gap-4" onSubmit={form.handleSubmit((v) => login.mutate(v))}>
      <Field label={t("identifierLabel")} error={form.formState.errors.identifier?.message} required>
        <Input autoComplete="username" {...form.register("identifier")} />
      </Field>
      <Field label={t("passwordLabel")} error={form.formState.errors.password?.message} required>
        <PasswordInput autoComplete="current-password" {...form.register("password")} />
      </Field>
      {loginError && <Alert tone="danger">{loginError}</Alert>}
      <Button type="submit" size="lg" block loading={login.isPending}>
        {t("common:signIn")}
      </Button>
    </form>
  );
}
