"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";

import { API_BASE_URL } from "@/lib/api";

type TerminalPanelProps = {
  token: string;
};

function websocketUrl(): string {
  const base = new URL(API_BASE_URL);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = "/ws/cloud-shell";
  base.search = "";
  return base.toString();
}

function formatOutput(data: MessageEvent<string>): string {
  try {
    const parsed = JSON.parse(data.data) as { output?: string; status?: string; metadata?: Record<string, unknown> };
    const status = parsed.status && parsed.status !== "success" ? `[${parsed.status}] ` : "";
    const audit = parsed.metadata?.audit_id ? `\r\n\r\nAudit ID: ${parsed.metadata.audit_id}` : "";
    return `${status}${parsed.output ?? ""}${audit}`;
  } catch {
    return data.data;
  }
}

export function TerminalPanel({ token }: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const bufferRef = useRef("");
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef<number | null>(null);
  const [connectionState, setConnectionState] = useState<"connecting" | "connected" | "disconnected">("connecting");

  useEffect(() => {
    if (!containerRef.current) return;

    const terminal = new Terminal({
      cursorBlink: true,
      convertEol: true,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
      fontSize: 13,
      rows: 28,
      theme: {
        background: "#0A0E15",
        foreground: "#E0E4EB",
        cursor: "#FFFFFF",
        selectionBackground: "#373F4E",
        black: "#0A0E15",
        blue: "#185FA5",
        cyan: "#B5D4F4",
        green: "#1D9E75",
        magenta: "#BFC6D4",
        red: "#A32D2D",
        white: "#FFFFFF",
        yellow: "#BA7517",
      },
    });
    terminal.open(containerRef.current);
    terminal.writeln("Connecting to Northbound Cloud Shell...");
    terminalRef.current = terminal;

    const socket = new WebSocket(websocketUrl(), ["northbound", token]);
    socketRef.current = socket;

    const prompt = () => terminal.write("\r\nnb> ");
    socket.onopen = () => {
      setConnectionState("connected");
    };
    socket.onmessage = (event) => {
      terminal.writeln(formatOutput(event));
      prompt();
    };
    socket.onerror = () => {
      terminal.writeln("\r\nConnection error. No secrets were logged.");
      setConnectionState("disconnected");
    };
    socket.onclose = () => {
      terminal.writeln("\r\nCloud Shell connection closed.");
      setConnectionState("disconnected");
    };

    const clearCurrentLine = () => {
      terminal.write("\r\u001b[2Knb> ");
    };

    const sendCommand = () => {
      const command = bufferRef.current.trim();
      terminal.write("\r\n");
      if (command && socket.readyState === WebSocket.OPEN) {
        historyRef.current.push(command);
        historyIndexRef.current = null;
        socket.send(command);
      } else if (!command) {
        prompt();
      } else {
        terminal.writeln("Cloud Shell is not connected.");
        prompt();
      }
      bufferRef.current = "";
    };

    const disposable = terminal.onData((data) => {
      if (data === "\r") {
        sendCommand();
        return;
      }
      if (data === "\u007F") {
        if (bufferRef.current.length > 0) {
          bufferRef.current = bufferRef.current.slice(0, -1);
          terminal.write("\b \b");
        }
        return;
      }
      if (data === "\u001b[A") {
        if (!historyRef.current.length) return;
        const nextIndex = historyIndexRef.current === null ? historyRef.current.length - 1 : Math.max(0, historyIndexRef.current - 1);
        historyIndexRef.current = nextIndex;
        bufferRef.current = historyRef.current[nextIndex];
        clearCurrentLine();
        terminal.write(bufferRef.current);
        return;
      }
      if (data === "\u001b[B") {
        if (historyIndexRef.current === null) return;
        const nextIndex = historyIndexRef.current + 1;
        if (nextIndex >= historyRef.current.length) {
          historyIndexRef.current = null;
          bufferRef.current = "";
        } else {
          historyIndexRef.current = nextIndex;
          bufferRef.current = historyRef.current[nextIndex];
        }
        clearCurrentLine();
        terminal.write(bufferRef.current);
        return;
      }
      if (data >= " " && data !== "\u007F") {
        bufferRef.current += data;
        terminal.write(data);
      }
    });

    return () => {
      disposable.dispose();
      socket.close();
      terminal.dispose();
    };
  }, [token]);

  return (
    <section className="min-h-[620px] overflow-hidden rounded-2xl border border-northbound-border bg-northbound-bg shadow-2xl shadow-black/20">
      <div className="flex items-center justify-between border-b border-northbound-border bg-northbound-panel px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-northbound-text">Northbound Cloud Shell</h2>
          <p className="text-xs text-northbound-textMuted">Controlled Operations Console</p>
        </div>
        <span className="rounded-full border border-northbound-border px-3 py-1 text-xs text-northbound-textMuted">
          {connectionState}
        </span>
      </div>
      <div ref={containerRef} className="h-[560px] p-3" aria-label="Northbound controlled cloud shell terminal" />
    </section>
  );
}

