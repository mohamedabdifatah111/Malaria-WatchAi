/**
 * Page behaviour with the API mocked. Every fixture below is a TEST FIXTURE shaped
 * like the backend serializers - not real surveillance evidence.
 */
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import * as endpoints from "../api/endpoints";
import { renderWithProviders } from "../test/utils";
import type { Brief, Paged, PrevalenceEstimate } from "../types/api";
import AssistantPage from "./AssistantPage";
import DrugEfficacyPage from "./DrugEfficacyPage";
import PrevalencePage from "./PrevalencePage";
import ResistancePage from "./ResistancePage";

vi.mock("../api/endpoints");
const m = vi.mocked(endpoints);
const empty = <T,>(message = "No validated evidence is available for the selected filters."): Paged<T> =>
  ({ items: [], pagination: null, dataStatus: "no_data", message });

beforeEach(() => {
  vi.resetAllMocks();
  m.getCountries.mockResolvedValue([{ code: "KEN", name: "Kenya" }]);
  m.getRegions.mockResolvedValue([{ id: 7, name: "Kisumu", country_code: "KEN", admin_level: "ADM1", parent_id: null, external_id: "X" }]);
  m.getPrevalenceUncertainty.mockResolvedValue(empty());
});

describe("PrevalencePage", () => {
  it("converts the 0-1 estimate to a percentage and labels it modelled", async () => {
    const row: PrevalenceEstimate = { country: "KEN", region_id: 7, region_name: "Kisumu", year: 2020, indicator: "PfPR",
      estimate: 0.196, lower_interval: 0.03, upper_interval: 0.629, source_type: "modelled", model_version: "0.1.0",
      evidence_ids: ["E10111"], status: "available" };
    m.getPrevalence.mockResolvedValue({ items: [row], pagination: null, dataStatus: "available" });
    renderWithProviders(<PrevalencePage />);
    expect(await screen.findByText("19.6%")).toBeInTheDocument();
    expect(screen.getByText("3.0% - 62.9%")).toBeInTheDocument();
    expect(screen.getAllByText("Modelled estimate").length).toBeGreaterThan(0);
    expect(screen.queryByText("0.196")).not.toBeInTheDocument();
  });

  it("shows the backend's no-data message instead of a fabricated chart", async () => {
    m.getPrevalence.mockResolvedValue(empty("No validated evidence is available for the selected filters."));
    renderWithProviders(<PrevalencePage />);
    expect(await screen.findByText("No validated evidence is available for the selected filters.")).toBeInTheDocument();
    expect(screen.getByText("No modelled estimates for this selection")).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    m.getPrevalence.mockRejectedValue(Object.assign(new Error("The server had a problem completing this request."), { status: 500 }));
    renderWithProviders(<PrevalencePage />);
    expect(await screen.findByText("The data could not be loaded.")).toBeInTheDocument();
  });
});

describe("DrugEfficacyPage and ResistancePage empty states", () => {
  it("does not treat missing studies as success or failure", async () => {
    m.getDrugEfficacy.mockResolvedValue(empty());
    renderWithProviders(<DrugEfficacyPage />);
    expect(await screen.findByText("Missing studies are not evidence of treatment success or failure.")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
  });

  it("states that no marker data exists", async () => {
    m.getResistance.mockResolvedValue(empty("No marker observations for this selection."));
    m.getResistanceTrends.mockResolvedValue(empty());
    renderWithProviders(<ResistancePage />);
    expect(await screen.findByText("No marker observations for this selection.")).toBeInTheDocument();
    expect(screen.getByText(/not proof of clinical treatment failure/)).toBeInTheDocument();
  });
});

describe("AssistantPage", () => {
  it("posts region_id null for a country-wide brief and renders findings", async () => {
    const brief: Brief = { brief_id: "b1", status: "draft", country: "KEN", region_id: null, summary: "Summary text.",
      findings: [{ topic: "prevalence", statement: "Finding statement text", evidence_ids: ["E1"] }],
      evidence_ids: ["E1"], uncertainties: [], limitations: ["Limit."], tool_trace_id: "t",
      created_at: "2026-11-13T09:00:00Z", edited_content: null, review: null };
    m.createBrief.mockResolvedValue(brief);
    renderWithProviders(<AssistantPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Generate brief" }));
    await waitFor(() => expect(m.createBrief).toHaveBeenCalled());
    expect(m.createBrief.mock.calls[0][0]).toMatchObject({ country: "KEN", region_id: null });
    expect(await screen.findByText("Finding statement text")).toBeInTheDocument();
  });

  it("shows a guardrail refusal clearly", async () => {
    // The real client always rejects with ApiError (see api/client.ts interceptor).
    m.createBrief.mockRejectedValue(new ApiError("This assistant cannot provide individual diagnosis.", 422, "GUARDRAIL_REFUSAL"));
    renderWithProviders(<AssistantPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Generate brief" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/refused|cannot provide/i);
  });
});
