import { describe, expect, it } from "vitest";

import { getBridge } from "./bridge";

describe("development bridge", () => {
  it("provides a safe mock snapshot and starts a run", async () => {
    const bridge = await getBridge();
    const snapshot = await bridge.bootstrap();

    expect(snapshot.ok).toBe(true);
    expect(snapshot.data?.models).toContain("flash");
    expect(snapshot.data?.config.tasks[0].agent_id).toBe("problem_analyst");

    const started = await bridge.startRun("测试主题", "flash");
    expect(started).toEqual({ ok: true, data: { accepted: true } });
  });
});
