import { useTranslation } from "@nirnoy/i18n";
import { Button, ErrorState } from "@nirnoy/ui";
import { Link } from "react-router";

/** Last-resort route boundary: never shows stack traces to users. */
export function RouteError() {
  const { t } = useTranslation();
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <ErrorState
        title={t("somethingWrong")}
        onRetry={() => window.location.reload()}
        retryLabel={t("retry")}
      />
      <div className="mt-2 flex justify-center">
        <Button asChild variant="link">
          <a href="/">{t("goHome")}</a>
        </Button>
      </div>
    </div>
  );
}

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex max-w-md animate-fade-up flex-col items-center gap-4 px-4 py-24 text-center">
      <p className="text-gradient font-display text-8xl font-extrabold leading-none tracking-tighter">404</p>
      <h1 className="text-2xl font-bold">{t("notFoundTitle")}</h1>
      <p className="text-muted">{t("notFoundBody")}</p>
      <Button asChild size="lg" className="mt-2">
        <Link to="/">{t("goHome")}</Link>
      </Button>
    </div>
  );
}
