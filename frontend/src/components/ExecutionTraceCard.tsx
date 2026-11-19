"use client";

import React, { useState } from "react";
import { ToolExecutionTrace } from "@/lib/types";
import { ChevronDown, ChevronUp, Clock, Zap, ShieldCheck, CheckCircle2, AlertCircle, Code2 } from "lucide-react";

interface ExecutionTraceCardProps {
  traces: ToolExecutionTrace[];
}

export function ExecutionTraceCard({ traces }: ExecutionTraceCardProps) {
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  if (!traces || traces.length === 0) return null;

  const totalTime = traces.reduce((acc, t) => acc + (t.execution_time_ms || 0), 0);

  return (
    <div className="w-full mb-3 rounded-xl border border-charcoal-700 bg-charcoal-950 overflow-hidden shadow-sm">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 bg-forest-900/40 hover:bg-forest-900/60 transition-colors text-left border-b border-forest-border/60 cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded-md bg-gold-500/15 text-gold-400 flex items-center justify-center">
            <Zap className="h-3 w-3 stroke-[2.5]" />
          </div>
          <span className="text-xs font-semibold text-zinc-100 tracking-wide flex items-center gap-1.5">
            Agent Execution Trace
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-charcoal-900 text-gold-300 border border-charcoal-700">
              {traces.length} {traces.length === 1 ? "Python tool" : "Python tools"}
            </span>
          </span>
        </div>

        <div className="flex items-center gap-2.5 text-zinc-400">
          <span className="text-[10px] font-mono text-zinc-400 flex items-center gap-1">
            <Clock className="h-2.5 w-2.5 text-gold-400" />
            {totalTime.toFixed(1)}ms
          </span>
          {isOpen ? <ChevronUp className="h-3.5 w-3.5 text-zinc-300" /> : <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />}
        </div>
      </button>

      {/* Trace Timeline Content */}
      {isOpen && (
        <div className="p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between pb-1.5 border-b border-charcoal-800 text-[10px] text-zinc-400 font-mono">
            <span className="flex items-center gap-1 text-emerald-400">
              <ShieldCheck className="h-3 w-3" /> Real Python Execution (Zero Simulated Data)
            </span>
            <span>Max Loop Guard: Active</span>
          </div>

          <div className="space-y-2">
            {traces.map((trace) => {
              const isSuccess = trace.status === "SUCCESS";
              const isExpanded = expandedStep === trace.step;
              const hasDetailedOutput = !!trace.output && Object.keys(trace.output).length > 0;

              return (
                <div
                  key={`step-${trace.step}-${trace.tool_name}`}
                  className="rounded-lg border border-charcoal-800 bg-charcoal-900/60 p-2.5 transition-all hover:border-charcoal-700"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold text-gold-400 bg-gold-500/10 px-1.5 py-0.5 rounded border border-gold-border/40">
                        Step {trace.step}
                      </span>
                      <code className="text-xs font-mono font-semibold text-zinc-200 bg-charcoal-800 px-1.5 py-0.5 rounded border border-charcoal-700">
                        {trace.tool_name}
                      </code>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono text-zinc-400">
                        {trace.execution_time_ms.toFixed(1)}ms
                      </span>
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded flex items-center gap-1 ${
                          isSuccess
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                            : "bg-red-950/80 text-red-300 border border-red-800/60"
                        }`}
                      >
                        {isSuccess ? <CheckCircle2 className="h-2.5 w-2.5" /> : <AlertCircle className="h-2.5 w-2.5" />}
                        {trace.status}
                      </span>
                    </div>
                  </div>

                  {/* Summary */}
                  <p className="mt-1.5 text-zinc-300 text-[11px] leading-relaxed">
                    {trace.result_summary}
                  </p>

                  {/* Arguments breakdown */}
                  {trace.arguments && Object.keys(trace.arguments).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1 items-center">
                      <span className="text-[10px] text-zinc-400 font-mono">Arguments:</span>
                      {Object.entries(trace.arguments).map(([key, val]) => {
                        if (val === null || val === undefined) return null;
                        return (
                          <span
                            key={key}
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-charcoal-800 text-zinc-300 border border-charcoal-700"
                          >
                            <span className="text-gold-400">{key}:</span> {typeof val === "object" ? JSON.stringify(val) : String(val)}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  {/* Verified JSON Payload Toggle */}
                  {hasDetailedOutput && (
                    <div className="mt-2 pt-1 border-t border-charcoal-800">
                      <button
                        onClick={() => setExpandedStep(isExpanded ? null : trace.step)}
                        className="text-[10px] font-mono text-zinc-400 hover:text-gold-300 flex items-center gap-1 cursor-pointer"
                      >
                        <Code2 className="h-2.5 w-2.5 text-gold-400" />
                        {isExpanded ? "Hide Verified Payload" : "Inspect Verified Output Payload"}
                      </button>

                      {isExpanded && (
                        <pre className="mt-1.5 p-2 rounded bg-charcoal-950 border border-charcoal-800 text-[10px] font-mono text-emerald-300 overflow-x-auto max-h-40">
                          {JSON.stringify(trace.output, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
