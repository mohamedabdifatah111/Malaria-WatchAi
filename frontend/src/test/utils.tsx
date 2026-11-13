import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import { BriefHistoryProvider } from "../context/BriefHistoryContext";
import { SelectionProvider } from "../context/SelectionContext";

/** Render with every provider the app uses. Data comes from mocked API modules (TEST FIXTURES). */
export function renderWithProviders(ui: ReactElement, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <SelectionProvider>
            <BriefHistoryProvider>{ui}</BriefHistoryProvider>
          </SelectionProvider>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
