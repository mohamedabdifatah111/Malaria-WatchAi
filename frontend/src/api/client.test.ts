import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";
import { ApiError, cleanParams, toApiError, unwrap, unwrapPaged } from "./client";

function axiosError(status: number | null, data?: unknown) {
  const err = new AxiosError("fail");
  if (status !== null) {
    err.response = { status, data, statusText: "", headers: {}, config: { headers: new AxiosHeaders() } };
  }
  return err;
}

describe("envelope handling", () => {
  it("unwraps {success, data, meta}", () => {
    expect(unwrap({ success: true, data: { token: "t" }, meta: {} })).toEqual({ token: "t" });
  });

  it("keeps the backend's no_data status and message for empty pages", () => {
    const r = unwrapPaged({ success: true, data: [], meta: { data_status: "no_data", message: "No validated evidence." } });
    expect(r.items).toEqual([]);
    expect(r.dataStatus).toBe("no_data");
    expect(r.message).toBe("No validated evidence.");
  });

  it("drops empty filter values instead of sending them", () => {
    expect(cleanParams({ country: "KEN", region_id: null, year: "", marker: undefined, page: 1 })).toEqual({ country: "KEN", page: 1 });
  });
});

describe("error normalisation", () => {
  it("uses the backend error envelope message and code", () => {
    const e = toApiError(axiosError(422, { success: false, error: { code: "GUARDRAIL_REFUSAL", message: "Refused." } }));
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(422);
    expect(e.code).toBe("GUARDRAIL_REFUSAL");
    expect(e.message).toBe("Refused.");
  });

  it("explains an unreachable server", () => {
    const e = toApiError(axiosError(null));
    expect(e.code).toBe("NETWORK_ERROR");
    expect(e.message).toMatch(/could not be reached/);
  });

  it("flags auth and permission failures", () => {
    expect(toApiError(axiosError(401, { detail: "Invalid token." })).isAuth).toBe(true);
    expect(toApiError(axiosError(403, { detail: "Reviewer permission is required." })).isForbidden).toBe(true);
  });
});
