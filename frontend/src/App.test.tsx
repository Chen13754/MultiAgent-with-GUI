import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Background: () => null,
  Controls: () => null,
  BackgroundVariant: { Dots: "dots" }
}));

import App, { wouldCreateCycle } from "./App";
import type { TaskConfig } from "./types";

describe("app shell", () => {
  it("loads the workbench and opens the configuration page", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("让多 Agent 协作变得可见")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "配置中心" }));
    expect(await screen.findByRole("heading", { name: "配置中心" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Agents" })).toBeInTheDocument();
  });

  it("rejects only edges that make the dependency graph cyclic", () => {
    const tasks: TaskConfig[] = [
      { id: "analysis", name: "Analysis", description: "", expected_output: "", agent_id: "a", context_task_ids: [], artifact_role: "none", enabled: true },
      { id: "review", name: "Review", description: "", expected_output: "", agent_id: "a", context_task_ids: ["analysis"], artifact_role: "none", enabled: true },
      { id: "summary", name: "Summary", description: "", expected_output: "", agent_id: "a", context_task_ids: ["review"], artifact_role: "none", enabled: true }
    ];

    expect(wouldCreateCycle(tasks, "analysis", "summary")).toBe(false);
    expect(wouldCreateCycle(tasks, "analysis", "review")).toBe(false);
    expect(wouldCreateCycle(tasks, "review", "analysis")).toBe(true);
  });
});
