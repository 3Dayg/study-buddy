import React, { useEffect } from "react";

export function Loader({ msg = "Loading…" }) {
  return (
    <div className="loader">
      <div className="spinner" />
      {msg}
    </div>
  );
}

export function Stat({ num, lbl, cls = "" }) {
  return (
    <div className="card stat">
      <div className={"num " + cls}>{num}</div>
      <div className="lbl">{lbl}</div>
    </div>
  );
}

export function ProgressBar({ pct, thin = false }) {
  return (
    <div className={"progress" + (thin ? " thin" : "")}>
      <span style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}

export function Toast({ toast }) {
  if (!toast) return null;
  return <div className={"toast " + (toast.kind || "")}>{toast.msg}</div>;
}

// Small hook to show auto-dismissing toasts.
export function useToast() {
  const [toast, setToast] = React.useState(null);
  const show = React.useCallback((msg, kind = "") => setToast({ msg, kind, id: Date.now() }), []);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);
  return [toast, show];
}

export function fmtDays(d) {
  if (d === null || d === undefined) return "";
  if (d < 1 / 24) return Math.max(1, Math.round(d * 1440)) + "m";
  if (d < 1) return Math.round(d * 24) + "h";
  if (d < 30) return Math.round(d) + "d";
  if (d < 365) return Math.round(d / 30) + "mo";
  return (d / 365).toFixed(1) + "y";
}
