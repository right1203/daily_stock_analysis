import type React from 'react';
import type { ReportStrategy as ReportStrategyType } from '../../types/analysis';
import { Card } from '../common';

interface ReportStrategyProps {
  strategy?: ReportStrategyType;
}

interface StrategyItemProps {
  label: string;
  value?: string;
  color: string;
}

const StrategyItem: React.FC<StrategyItemProps> = ({
  label,
  value,
  color,
}) => (
  <div className="relative overflow-hidden rounded-lg bg-elevated border border-white/5 p-3 hover:border-white/10 transition-colors">
    <div className="flex flex-col">
      <span className="text-xs text-muted mb-0.5">{label}</span>
      <span
        className="text-lg font-bold font-mono"
        style={{ color: value ? color : 'var(--text-muted)' }}
      >
        {value || '—'}
      </span>
    </div>
    {/* Bottom indicator bar */}
    <div
      className="absolute bottom-0 left-0 right-0 h-0.5"
      style={{ background: `linear-gradient(90deg, ${color}00, ${color}, ${color}00)` }}
    />
  </div>
);

/**
 * Strategy point section with terminal styling.
 */
export const ReportStrategy: React.FC<ReportStrategyProps> = ({ strategy }) => {
  if (!strategy) {
    return null;
  }

  const strategyItems = [
    {
      label: '이상 매수가',
      value: strategy.idealBuy,
      color: '#00ff88', // success
    },
    {
      label: '차선 매수가',
      value: strategy.secondaryBuy,
      color: '#00d4ff', // cyan
    },
    {
      label: '손절가',
      value: strategy.stopLoss,
      color: '#ff4466', // danger
    },
    {
      label: '목표가',
      value: strategy.takeProfit,
      color: '#ffaa00', // warning
    },
  ];

  return (
    <Card variant="bordered" padding="md">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="label-uppercase">STRATEGY POINTS</span>
        <h3 className="text-base font-semibold text-white">운용 가격대</h3>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {strategyItems.map((item) => (
          <StrategyItem key={item.label} {...item} />
        ))}
      </div>
    </Card>
  );
};
