import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Background: () => null,
  Controls: () => null,
  BackgroundVariant: { Dots: "dots" }
}));

import App from "./App";

describe("app shell", () => {
  it("loads the workbench and opens the configuration page", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("让多 Agent 协作变得可见")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "配置中心" }));
    expect(await screen.findByRole("heading", { name: "配置中心" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Agents" })).toBeInTheDocument();
  });
});
