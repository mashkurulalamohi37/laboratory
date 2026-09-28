import { useTranslation } from "@nirnoy/i18n";
import { EmptyState } from "@nirnoy/ui";
import { ShieldOff } from "lucide-react";

export function Forbidden() {
  const { t } = useTranslation("console");
  return (
    <EmptyState
      icon={<ShieldOff className="size-6" aria-hidden="true" />}
      title={t("forbidden")}
      className="py-24"
    />
  );
}
