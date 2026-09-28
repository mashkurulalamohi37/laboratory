import { Fragment, type ReactNode } from "react";

import { cn } from "../cn";

/**
 * Renders the CMS Markdown subset as React elements, never as raw HTML, so content cannot
 * inject markup or scripts:
 *
 *   # / ## / ### headings · paragraphs · "- " / "* " and "1. " lists · **bold** · *italic*
 *   `code` · [links](https://… | /path | mailto: | tel:)
 *
 * Anything else is shown as plain text. Headings start at `h{1 + headingOffset}` because
 * the page already has its own <h1>.
 */

const SAFE_HREF = /^(https?:\/\/|\/(?!\/)|mailto:|tel:)/i;

type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] };

export function parseBlocks(source: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
    if (list) blocks.push({ kind: "list", ...list });
    paragraph = [];
    list = null;
  };

  for (const raw of source.replace(/\r\n?/g, "\n").split("\n")) {
    const line = raw.trim();
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    const numbered = /^\d+[.)]\s+(.*)$/.exec(line);
    if (!line) {
      flush();
    } else if (heading) {
      flush();
      blocks.push({ kind: "heading", level: heading[1]!.length, text: heading[2]! });
    } else if (bullet || numbered) {
      const ordered = Boolean(numbered);
      if (paragraph.length || (list && list.ordered !== ordered)) flush();
      list ??= { ordered, items: [] };
      list.items.push((bullet ?? numbered)![1]!);
    } else if (list) {
      // A continuation line belongs to the last list item.
      list.items[list.items.length - 1] += ` ${line}`;
    } else {
      paragraph.push(line);
    }
  }
  flush();
  return blocks;
}

const INLINE = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;

export function renderInline(text: string, keyPrefix = "i"): ReactNode[] {
  return text.split(INLINE).map((part, i): ReactNode => {
    const key = `${keyPrefix}-${i}`;
    if (!part) return null;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code key={key} className="rounded bg-surface-muted px-1 py-0.5 text-[0.9em]">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    const link = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(part);
    if (link) {
      const [, label, href] = link;
      if (!SAFE_HREF.test(href!)) return <Fragment key={key}>{label}</Fragment>;
      const external = /^https?:/i.test(href!);
      return (
        <a
          key={key}
          href={href}
          className="text-brand-600 underline underline-offset-2 hover:text-brand-700"
          {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
        >
          {label}
        </a>
      );
    }
    return <Fragment key={key}>{part}</Fragment>;
  });
}

export function Markdown({
  source,
  headingOffset = 1,
  className,
}: {
  source: string;
  headingOffset?: number;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-4 leading-relaxed text-fg", className)}>
      {parseBlocks(source).map((block, i) => {
        if (block.kind === "heading") {
          const level = Math.min(block.level + headingOffset, 6);
          const Tag = `h${level}` as "h2";
          return (
            <Tag
              key={i}
              className={cn("font-semibold text-fg", level <= 2 ? "mt-2 text-xl" : "text-lg")}
            >
              {renderInline(block.text, `h${i}`)}
            </Tag>
          );
        }
        if (block.kind === "list") {
          const List = block.ordered ? "ol" : "ul";
          return (
            <List
              key={i}
              className={cn("flex flex-col gap-1 pl-6", block.ordered ? "list-decimal" : "list-disc")}
            >
              {block.items.map((item, j) => (
                <li key={j}>{renderInline(item, `l${i}-${j}`)}</li>
              ))}
            </List>
          );
        }
        return <p key={i}>{renderInline(block.text, `p${i}`)}</p>;
      })}
    </div>
  );
}
