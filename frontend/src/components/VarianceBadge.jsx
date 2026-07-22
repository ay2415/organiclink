import React from 'react';
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react';

const VarianceBadge = ({ variancePercent, acceptable, isAnomaly }) => {
  if (variancePercent === null || variancePercent === undefined) return null;

  if (isAnomaly) {
    return (
      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold">
        <Info className="w-4 h-4 text-blue-600" />
        <span>Quality Improved ({variancePercent.toFixed(1)}% drop) — Accepted</span>
      </div>
    );
  }

  if (acceptable) {
    return (
      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-bold">
        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
        <span>PASS: {variancePercent.toFixed(1)}% Variance (Within ±10% Tolerance)</span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 border border-red-300 text-red-800 text-xs font-bold animate-pulse">
      <AlertTriangle className="w-4 h-4 text-red-600" />
      <span>DISPUTE: {variancePercent.toFixed(1)}% Variance (Exceeds 10% Tolerance)</span>
    </div>
  );
};

export default VarianceBadge;
