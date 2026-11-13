import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ApiError } from "./api/client";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { BriefHistoryProvider } from "./context/BriefHistoryContext";
import { SelectionProvider } from "./context/SelectionContext";
import "leaflet/dist/leaflet.css";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      // Do not retry auth/permission/validation failures; retry network/server errors once.
      retry: (count, err) => !(err instanceof ApiError && err.status !== null && err.status < 500) && count < 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <SelectionProvider>
            <BriefHistoryProvider>
              <App />
            </BriefHistoryProvider>
          </SelectionProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
