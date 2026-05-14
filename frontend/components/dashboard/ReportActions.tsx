"use client";

import { ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/Button";

type ReportActionsProps = {
  onGenerateExecutive?: () => void;
  onGenerateTechnical?: () => void;
  onPreviewLatest?: () => void;
  onDownloadLatest?: () => void;
  onPrint?: () => void;
  isBusy?: boolean;
};

export function ReportActions({
  onGenerateExecutive,
  onGenerateTechnical,
  onPreviewLatest,
  onDownloadLatest,
  onPrint,
  isBusy,
}: ReportActionsProps) {
  return (
    <div id="reports" className="flex flex-wrap gap-2">
      <Button variant="primary" onClick={onGenerateExecutive} disabled={isBusy}>
        <ClipboardList size={15} aria-hidden="true" />
        Generate Executive Report
      </Button>
      <Button variant="secondary" onClick={onGenerateTechnical} disabled={isBusy}>
        <ClipboardList size={15} aria-hidden="true" />
        Generate Technical Report
      </Button>
      <Button variant="secondary" onClick={onPreviewLatest}>
        <ClipboardList size={15} aria-hidden="true" />
        Preview Latest
      </Button>
      <Button variant="secondary" onClick={onDownloadLatest}>
        <ClipboardList size={15} aria-hidden="true" />
        Download PDF
      </Button>
      <Button variant="secondary" onClick={onPrint}>
        <ClipboardList size={15} aria-hidden="true" />
        Print
      </Button>
    </div>
  );
}
