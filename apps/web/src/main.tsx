import "./styles.css";

import { AuthProvider, CartProvider, createQueryClient } from "@nirnoy/app-core";
import { initI18n } from "@nirnoy/i18n";
import { Toaster } from "@nirnoy/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";

import { app } from "./api";
import { router } from "./router";

initI18n();
const queryClient = createQueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider app={app}>
        <CartProvider>
          <RouterProvider router={router} />
          <Toaster position="top-center" richColors closeButton />
        </CartProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
