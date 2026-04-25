import React from 'react';
import type { AnalysisResult, AnalysisReport } from '../../types/analysis';
import { ReportOverview } from './ReportOverview';
import { ReportStrategy } from './ReportStrategy';
import { ReportNews } from './ReportNews';
import { ReportDetails } from './ReportDetails';

interface ReportSummaryProps {
  data: AnalysisResult | AnalysisReport;
  isHistory?: boolean;
}

/**
 * Full report display component
 * Combines the overview, strategy, news, and details sections
 */
export const ReportSummary: React.FC<ReportSummaryProps> = ({
  data,
  isHistory = false,
}) => {
  // Support both AnalysisResult and AnalysisReport data shapes
  const report: AnalysisReport = 'report' in data ? data.report : data;
  // Use report id because queryId may repeat in batch analysis, and the history detail API needs recordId to fetch related news and detail data
  const recordId = report.meta.id;

  const { meta, summary, strategy, details } = report;
  const modelUsed = (meta.modelUsed || '').trim();
  const shouldShowModel = Boolean(
    modelUsed && !['unknown', 'error', 'none', 'null', 'n/a'].includes(modelUsed.toLowerCase()),
  );

  return (
    <div className="space-y-3 animate-fade-in">
      {/* Overview section (first screen) */}
      <ReportOverview
        meta={meta}
        summary={summary}
        isHistory={isHistory}
      />

      {/* Strategy price levels section */}
      <ReportStrategy strategy={strategy} />

      {/* News section */}
      <ReportNews recordId={recordId} />

      {/* Transparency and traceability section */}
      <ReportDetails details={details} recordId={recordId} />

      {/* Analysis model marker (Issue #528), shown at the end of the report */}
      {shouldShowModel && (
        <p className="text-xs text-gray-500 mt-3">
          분석 모델: {modelUsed}
        </p>
      )}
    </div>
  );
};
