import { describe, expect, it } from "vitest";
import {
  fractionInterval, fractionToPercent, integer, NOT_AVAILABLE, percent, percentInterval, riskClassOf,
} from "./format";

describe("prevalence fractions", () => {
  it("multiplies 0-1 fractions by 100 for display", () => {
    expect(fractionToPercent(0.05)).toBe("5.0%");
    expect(fractionToPercent(0.12)).toBe("12.0%");
    expect(fractionToPercent(0.196)).toBe("19.6%");
    expect(fractionToPercent(0)).toBe("0.0%"); // a real zero stays zero
  });

  it("never shows a missing value as zero", () => {
    expect(fractionToPercent(null)).toBe(NOT_AVAILABLE);
    expect(fractionToPercent(undefined)).toBe(NOT_AVAILABLE);
    expect(fractionToPercent(Number.NaN)).toBe(NOT_AVAILABLE);
    expect(integer(null)).toBe(NOT_AVAILABLE);
  });

  it("formats intervals and refuses partial ones", () => {
    expect(fractionInterval(0.03, 0.629)).toBe("3.0% - 62.9%");
    expect(fractionInterval(0.03, null)).toBe(NOT_AVAILABLE);
  });
});

describe("efficacy percentages", () => {
  it("does not multiply values that are already percentages", () => {
    expect(percent(96.9)).toBe("96.9%");
    expect(percentInterval(93.8, 98.4)).toBe("93.8% - 98.4%");
    expect(percent(null)).toBe(NOT_AVAILABLE);
  });
});

describe("risk classes", () => {
  it("uses lower-bound-inclusive cut points 1%, 10%, 35%", () => {
    expect(riskClassOf(0.0099)).toBe("very_low");
    expect(riskClassOf(0.01)).toBe("low");
    expect(riskClassOf(0.0999)).toBe("low");
    expect(riskClassOf(0.1)).toBe("moderate");
    expect(riskClassOf(0.35)).toBe("high");
    expect(riskClassOf(null)).toBeNull();
  });
});
