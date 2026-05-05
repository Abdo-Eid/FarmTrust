interface ReportSummaryTextProps {
  text: string
}

export function ReportSummaryText({ text }: ReportSummaryTextProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-5 shadow-panel">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Assessment Summary</p>
      <p className="text-sm text-gray-700 leading-relaxed">{text}</p>
    </div>
  )
}
