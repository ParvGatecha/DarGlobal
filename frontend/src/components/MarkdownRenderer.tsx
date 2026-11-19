"use client";

import React from "react";
import { Citation } from "@/lib/types";

interface MarkdownRendererProps {
  content: string;
  citations?: Citation[];
  onSelectCitation?: (citation: Citation) => void;
}

export function MarkdownRenderer({ content, citations, onSelectCitation }: MarkdownRendererProps) {
  const lines = (content || "").split("\n");

  const renderFormattedText = (text: string) => {
    const parts: React.ReactNode[] = [];
    const citationRegex = /\[(\d+)\]/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = citationRegex.exec(text)) !== null) {
      const matchIndex = match.index;
      const citationId = parseInt(match[1], 10);

      if (matchIndex > lastIndex) {
        parts.push(renderBoldText(text.substring(lastIndex, matchIndex), `pre-${matchIndex}`));
      }

      const matchedCitation = citations?.find((c) => c.citation_id === citationId);

      parts.push(
        <button
          key={`cit-${matchIndex}-${citationId}`}
          onClick={() => matchedCitation && onSelectCitation && onSelectCitation(matchedCitation)}
          className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 rounded bg-gold-500/20 hover:bg-gold-500/40 text-gold-300 border border-gold-border/80 text-[10px] font-mono font-bold transition-all cursor-pointer hover:scale-105"
          title={matchedCitation ? `${matchedCitation.title} (${matchedCitation.source})` : `Citation [${citationId}]`}
        >
          [{citationId}]
        </button>
      );

      lastIndex = matchIndex + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(renderBoldText(text.substring(lastIndex), `post-${lastIndex}`));
    }

    return parts.length > 0 ? parts : renderBoldText(text, "full");
  };

  const renderBoldText = (str: string, keyPrefix: string) => {
    const boldParts = str.split(/(\*\*[^*]+\*\*)/g);
    return boldParts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={`${keyPrefix}-b-${i}`} className="font-semibold text-zinc-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return <span key={`${keyPrefix}-t-${i}`}>{part}</span>;
    });
  };

  // Process blocks (detecting tables vs regular lines)
  const renderedElements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Table Detection
    if (trimmed.startsWith("|") && trimmed.endsWith("|") && i + 1 < lines.length && lines[i + 1].trim().startsWith("|") && lines[i + 1].includes("---")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const headerRow = tableLines[0]
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        const dataRows = tableLines.slice(2).map((rowStr) =>
          rowStr
            .split("|")
            .slice(1, -1)
            .map((c) => c.trim())
        );

        renderedElements.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-charcoal-700 bg-charcoal-950 shadow-md">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-forest-900 border-b border-forest-border text-gold-300 font-semibold uppercase tracking-wider text-[10px] font-mono">
                <tr>
                  {headerRow.map((col, idx) => (
                    <th key={`th-${idx}`} className="px-3 py-2.5 whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-charcoal-800">
                {dataRows.map((row, rIdx) => (
                  <tr key={`tr-${rIdx}`} className="hover:bg-charcoal-850/60 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={`td-${rIdx}-${cIdx}`} className="px-3 py-2 text-zinc-300">
                        {renderFormattedText(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 2. Empty spacing
    if (!trimmed) {
      renderedElements.push(<div key={`empty-${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    // 3. Headers
    if (trimmed.startsWith("### ")) {
      renderedElements.push(
        <h3 key={`h3-${i}`} className="text-base font-serif font-bold text-gold-300 mt-3 mb-1">
          {renderFormattedText(trimmed.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith("#### ")) {
      renderedElements.push(
        <h4 key={`h4-${i}`} className="text-sm font-semibold text-zinc-100 mt-2.5 mb-1 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-gold-400"></span>
          {renderFormattedText(trimmed.slice(5))}
        </h4>
      );
      i++;
      continue;
    }

    // 4. Alerts / Quotes
    if (trimmed.startsWith("> ")) {
      renderedElements.push(
        <div
          key={`quote-${i}`}
          className="p-3 my-2.5 rounded-xl bg-forest-900/40 border-l-2 border-gold-400 text-xs text-zinc-300 leading-relaxed font-sans shadow-sm"
        >
          {renderFormattedText(trimmed.slice(2).replace("[!NOTE]", "").trim())}
        </div>
      );
      i++;
      continue;
    }

    // 5. Bullets
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      renderedElements.push(
        <div key={`bullet-${i}`} className="flex items-start gap-2.5 pl-1.5 py-0.5">
          <span className="text-gold-400 text-xs leading-5">-</span>
          <span className="flex-1 text-zinc-300 text-xs leading-relaxed">{renderFormattedText(trimmed.slice(2))}</span>
        </div>
      );
      i++;
      continue;
    }

    // 6. Regular Paragraph
    renderedElements.push(
      <p key={`p-${i}`} className="text-xs sm:text-sm text-zinc-300 leading-relaxed">
        {renderFormattedText(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-1 font-sans">{renderedElements}</div>;
}
