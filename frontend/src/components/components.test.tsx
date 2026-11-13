import { render, screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ProtectedRoute } from "../App";
import { surveyRate } from "../pages/SpeciesPage";
import { renderWithProviders } from "../test/utils";
import type { Brief, SpeciesRecord } from "../types/api";
import { briefPayload } from "./BriefForm";
import { BriefView, findingText } from "./BriefView";
import { ErrorState, Kpi, SpeciesRecordBadge } from "./ui";

// TEST FIXTURE shaped like backend BriefSerializer output - not real evidence.
const BRIEF: Brief = {
  brief_id: "b1", status: "draft", country: "KEN", region_id: null,
  summary: "Validated evidence was retrieved for Kenya.",
  findings: [
    { topic: "prevalence", statement: "Kisumu (2020): modelled PfPR estimate 0.196", evidence_ids: ["E10111"] },
    { text: "Finding using the alternative text shape" },
  ],
  evidence_ids: ["E10111"], uncertainties: ["No validated parasite species evidence is available for this area."],
  limitations: ["Modelled estimates are not observed measurements."], tool_trace_id: "t1",
  created_at: "2026-11-13T09:00:00Z", edited_content: null, review: null,
};

describe("briefs", () => {
  it("renders findings objects by statement (and text), never as [object Object]", () => {
    render(<BriefView brief={BRIEF} />);
    expect(screen.getByText("Kisumu (2020): modelled PfPR estimate 0.196")).toBeInTheDocument();
    expect(screen.getByText("Finding using the alternative text shape")).toBeInTheDocument();
    expect(screen.queryByText(/\[object Object\]/)).not.toBeInTheDocument();
    expect(screen.getByText(/country level/)).toBeInTheDocument();
    expect(screen.getByText(/Draft - awaiting human review/)).toBeInTheDocument();
    expect(screen.getByText(/No validated parasite species evidence/)).toBeInTheDocument();
  });

  it("extracts finding text from either shape", () => {
    expect(findingText({ statement: "a" })).toBe("a");
    expect(findingText({ text: "b" })).toBe("b");
    expect(findingText("c")).toBe("c");
  });

  it("sends region_id: null for a country-wide brief", () => {
    expect(briefPayload("KEN", null, " Summarise ")).toEqual({ country: "KEN", region_id: null, question: "Summarise" });
    expect(briefPayload("TZA", 42, "q?")).toEqual({ country: "TZA", region_id: 42, question: "q?" });
  });

  it("shows no approval controls", () => {
    render(<BriefView brief={BRIEF} />);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });
});

describe("species", () => {
  const presence: SpeciesRecord = { country: "KEN", region_id: null, species: "P. falciparum", record_type: "presence_only",
    positive: null, examined: null, year: 2023, source_id: "E10001", evidence_ids: ["E10001"] };
  const survey: SpeciesRecord = { ...presence, record_type: "survey", positive: 12, examined: 100 };

  it("never computes a rate from presence-only records", () => {
    expect(surveyRate(presence)).toBeNull();
    expect(surveyRate(survey)).toBeCloseTo(0.12);
  });

  it("labels presence-only records as presence observations", () => {
    render(<SpeciesRecordBadge type="presence_only" />);
    expect(screen.getByText("Presence observation only")).toBeInTheDocument();
  });
});

describe("states", () => {
  it("KPI shows 'Not available' instead of a zero", () => {
    render(<Kpi label="Survey locations" value={null} />);
    expect(screen.getByText("Not available")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("explains a 403 as missing reviewer permission", () => {
    render(<ErrorState error={{ status: 403, message: "Reviewer permission is required." }} />);
    expect(screen.getByText(/requires reviewer permission/)).toBeInTheDocument();
  });

  it("redirects unauthenticated users to login", () => {
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<p>Login screen</p>} />
        <Route path="/dashboard" element={<ProtectedRoute><p>Secret dashboard</p></ProtectedRoute>} />
      </Routes>,
      "/dashboard",
    );
    expect(screen.getByText("Login screen")).toBeInTheDocument();
    expect(screen.queryByText("Secret dashboard")).not.toBeInTheDocument();
  });

  it("lets authenticated users through", () => {
    sessionStorage.setItem("mwai.token", "test-token");
    renderWithProviders(
      <Routes>
        <Route path="/dashboard" element={<ProtectedRoute><p>Secret dashboard</p></ProtectedRoute>} />
      </Routes>,
      "/dashboard",
    );
    expect(screen.getByText("Secret dashboard")).toBeInTheDocument();
  });
});

