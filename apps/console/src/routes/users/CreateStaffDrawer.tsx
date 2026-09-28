import { zodResolver } from "@hookform/resolvers/zod";
import { ApiError, unwrap } from "@nirnoy/api-client";
import { useAuth, useErrorMessage } from "@nirnoy/app-core";
import { normalizeBDPhone, useTranslation } from "@nirnoy/i18n";
import { Alert, Button, Drawer, Field, Input, PasswordInput, PhoneInput, Select, toast } from "@nirnoy/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useRoles } from "./useRoles";

type FormValues = {
  full_name: string;
  phone: string;
  email: string;
  password: string;
  role: string;
};

export function CreateStaffDrawer({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (userId: string) => void;
}) {
  const { t } = useTranslation("console");
  const { api } = useAuth();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const roles = useRoles();
  const staffRoles = (roles.data ?? []).filter((r) => r.code !== "PATIENT");

  const schema = z.object({
    full_name: z.string().trim().min(2).max(150),
    phone: z.string().refine((v) => normalizeBDPhone(v) !== null, t("auth:phoneInvalid")),
    email: z.union([z.literal(""), z.string().email()]),
    password: z
      .string()
      .min(10, t("auth:passwordHint"))
      .regex(/[A-Za-z]/, t("auth:passwordHint"))
      .regex(/\d/, t("auth:passwordHint")),
    role: z.string().min(1),
  });
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", phone: "", email: "", password: "", role: "" },
  });

  const create = useMutation({
    mutationFn: (v: FormValues) =>
      unwrap(
        api.POST("/api/v1/admin/users", {
          body: {
            full_name: v.full_name,
            phone: normalizeBDPhone(v.phone)!,
            email: v.email || null,
            password: v.password,
            role: v.role,
            scope_type: "GLOBAL",
          },
        }),
      ),
    onSuccess: async (user) => {
      toast.success(t("users.created"));
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      form.reset();
      onOpenChange(false);
      onCreated(user.id);
    },
    onError: (err) => {
      // Map server-side validation errors onto the matching fields.
      if (err instanceof ApiError) {
        Object.entries(err.fieldErrors()).forEach(([field, issue]) => {
          if (field in schema.shape) form.setError(field as keyof FormValues, { message: issue });
        });
      }
    },
  });

  const e = form.formState.errors;
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("users.create")}
      description={t("users.createDescription")}
      closeLabel={t("common:close")}
      footer={
        <>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            {t("common:cancel")}
          </Button>
          <Button type="submit" form="create-staff" loading={create.isPending}>
            {t("users.create")}
          </Button>
        </>
      }
    >
      <form
        id="create-staff"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={form.handleSubmit((v) => create.mutate(v))}
      >
        <Field label={t("users.name")} error={e.full_name?.message} required>
          <Input autoComplete="off" {...form.register("full_name")} />
        </Field>
        <Field label={t("users.phone")} hint={t("auth:phoneHint")} error={e.phone?.message} required>
          <PhoneInput autoComplete="off" {...form.register("phone")} />
        </Field>
        <Field label={t("users.email")} error={e.email?.message}>
          <Input type="email" autoComplete="off" {...form.register("email")} />
        </Field>
        <Field label={t("users.role")} error={e.role?.message} required>
          <Select {...form.register("role")} disabled={roles.isPending}>
            <option value="" disabled>
              —
            </option>
            {staffRoles.map((r) => (
              <option key={r.code} value={r.code}>
                {r.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          label={t("users.initialPassword")}
          hint={t("auth:passwordHint")}
          error={e.password?.message}
          required
        >
          <PasswordInput autoComplete="new-password" {...form.register("password")} />
        </Field>
        {create.error && <Alert tone="danger">{errorMessage(create.error)}</Alert>}
      </form>
    </Drawer>
  );
}
