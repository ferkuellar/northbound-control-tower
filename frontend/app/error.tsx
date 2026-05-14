"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("Dashboard rendering error", { digest: error.digest });
    }
  }, [error.digest]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-northbound-black100 px-6 text-northbound-white100">
      <section className="w-full max-w-md rounded-lg border border-northbound-black80 bg-northbound-black90 p-6 shadow-xl">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-400">Northbound Control Tower</p>
        <h1 className="mt-3 text-2xl font-semibold">Dashboard unavailable</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">The dashboard could not render this view.</p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 rounded-md border border-northbound-black80 bg-northbound-white90 px-4 py-2 text-sm font-medium text-northbound-black100 hover:bg-northbound-white100"
        >
          Retry
        </button>
      </section>
    </main>
  );
}
