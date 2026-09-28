import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  Button,
  ConfirmDialog,
  DataTable,
  Field,
  Input,
  Markdown,
  OtpInput,
  parseBlocks,
  SearchBox,
  Tabs,
} from "./index";

describe("Button", () => {
  it("is disabled and busy while loading", () => {
    render(<Button loading>Save</Button>);
    const btn = screen.getByRole("button", { name: "Save" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
  });
});

describe("Field", () => {
  it("links label, hint and error to the control", () => {
    const { rerender } = render(
      <Field label="Mobile number" hint="e.g. 01712-345678">
        <Input />
      </Field>,
    );
    const input = screen.getByLabelText("Mobile number");
    expect(input).toHaveAccessibleDescription("e.g. 01712-345678");
    expect(input).not.toHaveAttribute("aria-invalid");

    rerender(
      <Field label="Mobile number" hint="e.g. 01712-345678" error="Invalid number">
        <Input />
      </Field>,
    );
    expect(screen.getByLabelText("Mobile number")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid number");
  });
});

describe("OtpInput", () => {
  it("keeps digits only, up to the length", async () => {
    render(<OtpInput aria-label="code" />);
    const input = screen.getByLabelText("code");
    await userEvent.type(input, "12a3-4567");
    expect(input).toHaveValue("123456");
    expect(input).toHaveAttribute("autocomplete", "one-time-code");
  });
});

describe("DataTable", () => {
  const columns = [{ key: "name", header: "Name", cell: (r: { name: string }) => r.name }];

  it("renders empty, error and loading states", () => {
    const { rerender } = render(
      <DataTable columns={columns} rows={[]} rowKey={(r) => r.name} caption="People"
        empty={{ title: "No people" }} />,
    );
    expect(screen.getByText("No people")).toBeInTheDocument();

    const onRetry = vi.fn();
    rerender(
      <DataTable columns={columns} rows={undefined} rowKey={(r) => r.name} caption="People"
        empty={{ title: "No people" }} error={{ title: "Failed", requestId: "req-9", onRetry }} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("req-9");

    rerender(
      <DataTable columns={columns} rows={undefined} rowKey={(r) => r.name} caption="People"
        empty={{ title: "No people" }} isLoading loadingLabel="Loading people" />,
    );
    expect(screen.getByRole("status", { name: "Loading people" })).toBeInTheDocument();
  });

  it("activates rows from the keyboard", async () => {
    const onRowClick = vi.fn();
    render(
      <DataTable columns={columns} rows={[{ name: "Rahim" }]} rowKey={(r) => r.name}
        caption="People" empty={{ title: "none" }} onRowClick={onRowClick} />,
    );
    const row = screen.getAllByText("Rahim")[0]!.closest("tr")!;
    row.focus();
    await userEvent.keyboard("{Enter}");
    expect(onRowClick).toHaveBeenCalledWith({ name: "Rahim" });
  });
});

describe("ConfirmDialog", () => {
  it("requires typing the confirmation text for destructive actions", async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog open onOpenChange={() => {}} title="Disable account" confirmLabel="Disable"
        destructive confirmText="Rahim" onConfirm={onConfirm} />,
    );
    const confirm = screen.getByRole("button", { name: "Disable" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox"), "Rahim");
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});

describe("Markdown", () => {
  it("renders the subset as elements and never passes HTML through", () => {
    const { container } = render(
      <Markdown
        source={"# Title\n\nHello **world** and *you*.\n\n- one\n- two\n\n<script>alert(1)</script>"}
      />,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Title" })).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("world");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(container.querySelector("script")).toBeNull();
    expect(container).toHaveTextContent("<script>alert(1)</script>");
  });

  it("only links safe URLs", () => {
    render(<Markdown source={"[ok](/tests) [bad](javascript:alert(1)) [ext](https://x.example)"} />);
    expect(screen.getByRole("link", { name: "ok" })).toHaveAttribute("href", "/tests");
    expect(screen.queryByRole("link", { name: "bad" })).toBeNull();
    expect(screen.getByRole("link", { name: "ext" })).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("groups list items and ordered lists", () => {
    expect(parseBlocks("1. a\n2. b\n\npara\nline")).toEqual([
      { kind: "list", ordered: true, items: ["a", "b"] },
      { kind: "paragraph", text: "para line" },
    ]);
  });
});

describe("SearchBox", () => {
  const suggestions = [
    { key: "t1", group: "test", label: "Fasting Blood Sugar" },
    { key: "t2", group: "test", label: "HbA1c" },
    { key: "p1", group: "package", label: "Diabetes Screening" },
  ];

  function Harness({ onSelect, onSubmit }: { onSelect: (k: string) => void; onSubmit: (q: string) => void }) {
    const [value, setValue] = useState("");
    return (
      <SearchBox
        value={value}
        onValueChange={setValue}
        suggestions={value.length >= 2 ? suggestions : []}
        groupLabels={{ test: "Tests", package: "Packages" }}
        onSelect={(s) => onSelect(s.key)}
        onSubmit={onSubmit}
        label="Search"
        submitLabel="Go"
        clearLabel="Clear"
        emptyText="None"
      />
    );
  }

  it("navigates grouped suggestions with the keyboard", async () => {
    const onSelect = vi.fn();
    const onSubmit = vi.fn();
    render(<Harness onSelect={onSelect} onSubmit={onSubmit} />);
    const input = screen.getByRole("combobox", { name: "Search" });
    await userEvent.type(input, "su");
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("group", { name: "Packages" })).toBeInTheDocument();
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(screen.getByRole("option", { name: "HbA1c" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("t2");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits the free-text query when no suggestion is active", async () => {
    const onSubmit = vi.fn();
    render(<Harness onSelect={vi.fn()} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByRole("combobox"), "sugar{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("sugar");
  });
});

describe("Tabs", () => {
  it("moves between tabs with arrow keys", async () => {
    function Harness() {
      const [tab, setTab] = useState("a");
      return (
        <Tabs
          label="Sections"
          value={tab}
          onValueChange={setTab}
          items={[
            { id: "a", label: "Alpha", content: <p>first</p> },
            { id: "b", label: "Beta", content: <p>second</p> },
          ]}
        />
      );
    }
    render(<Harness />);
    screen.getByRole("tab", { name: "Alpha" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("second")).toBeVisible();
  });
});
