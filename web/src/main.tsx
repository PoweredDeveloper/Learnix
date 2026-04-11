import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { captureKeyFromQuery } from "@/api";
import App from "./App.tsx";
import "./index.css";

// Before any route or child effect runs: persist ?key= from Telegram WebApp / magic link.
captureKeyFromQuery();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
