import type React from 'react';
import type { ReportMeta, ReportSummary as ReportSummaryType } from '../../types/analysis';
import { ScoreGauge, Card } from '../common';
import { formatDateTime } from '../../utils/format';

interface ReportOverviewProps {
  meta: ReportMeta;
  summary: ReportSummaryType;
  isHistory?: boolean;
}

/**
 * Report overview section with terminal styling.
 */
export const ReportOverview: React.FC<ReportOverviewProps> = ({
  meta,
  summary
}) => {
  // Return color class for price change.
  const getPriceChangeColor = (changePct: number | undefined): string => {
    if (changePct === undefined || changePct === null) return 'text-muted';
    if (changePct > 0) return 'text-[#ff4d4d]'; // red for gains
    if (changePct < 0) return 'text-[#00d46a]'; // green for losses
    return 'text-muted';
  };

  // Format price change percentage.
  const formatChangePct = (changePct: number | undefined): string => {
    if (changePct === undefined || changePct === null) return '--';
    const sign = changePct > 0 ? '+' : '';
    return `${sign}${changePct.toFixed(2)}%`;
  };

  return (
    <div className="space-y-4">
      {/* Main info area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
        {/* Left: stock info and conclusion */}
        <div className="lg:col-span-2 space-y-4">
          {/* Stock header */}
          <Card variant="gradient" padding="md">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold text-white">
                    {meta.stockName || meta.stockCode}
                  </h2>
                  {/* Price and change percentage */}
                  {meta.currentPrice != null && (
                    <div className="flex items-baseline gap-2">
                      <span className={`text-xl font-bold font-mono ${getPriceChangeColor(meta.changePct)}`}>
                        {meta.currentPrice.toFixed(2)}
                      </span>
                      <span className={`text-sm font-semibold font-mono ${getPriceChangeColor(meta.changePct)}`}>
                        {formatChangePct(meta.changePct)}
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="font-mono text-xs text-cyan bg-cyan/10 px-1.5 py-0.5 rounded">
                    {meta.stockCode}
                  </span>
                  <span className="text-xs text-muted flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {formatDateTime(meta.createdAt)}
                  </span>
                </div>
              </div>
            </div>

            {/* Key conclusion */}
            <div className="border-t border-white/5 pt-4">
              <span className="label-uppercase">KEY INSIGHTS</span>
              <p className="text-white text-sm leading-relaxed mt-1.5 whitespace-pre-wrap text-left">
                {summary.analysisSummary || '분석 결론이 없습니다'}
              </p>
            </div>
          </Card>

          {/* Operation advice and trend prediction */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Operation advice */}
            <Card variant="bordered" padding="sm" hoverable>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-xs font-medium text-success mb-0.5">운용 제안</h4>
                  <p className="text-white text-sm font-medium">
                    {summary.operationAdvice || '제안 없음'}
                  </p>
                </div>
              </div>
            </Card>

            {/* Trend prediction */}
            <Card variant="bordered" padding="sm" hoverable>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-warning/10 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-xs font-medium text-warning mb-0.5">추세 전망</h4>
                  <p className="text-white text-sm font-medium">
                    {summary.trendPrediction || '전망 없음'}
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Right: sentiment gauge */}
        <div className="flex flex-col self-stretch min-h-full">
          <Card variant="bordered" padding="md" className="!overflow-visible flex-1 flex flex-col min-h-0">
            <div className="text-center flex-1 flex flex-col justify-center">
              <h3 className="text-sm font-medium text-white mb-4">Market Sentiment</h3>
              <ScoreGauge score={summary.sentimentScore} size="lg" />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
