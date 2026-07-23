import React from 'react';
import GradeBadge from './GradeBadge';

const CVBreakdownPanel = ({ inspection, title = "Computer Vision Quality Inspection" }) => {
  if (!inspection || !inspection.quality_grade) {
    return (
      <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 text-slate-700 text-xs font-semibold text-center">
        Visual grading not applicable
      </div>
    );
  }

  const cv = inspection.cv_results || {};
  const probs = cv.class_probabilities || {};

  return (
    <div className="bg-white rounded-xl p-5 border border-emerald-100 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-gray-100 pb-3">
        <h4 className="font-bold text-gray-800 text-base">{title}</h4>
        <GradeBadge grade={inspection.quality_grade} score={inspection.quality_score} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
          <span className="text-gray-500 block">Colour Vibrancy</span>
          <span className="text-base font-bold text-emerald-900">{cv.colour_vibrancy?.toFixed(1) || 85.0} / 100</span>
        </div>
        <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
          <span className="text-gray-500 block">Colour Uniformity</span>
          <span className="text-base font-bold text-emerald-900">{cv.colour_uniformity?.toFixed(1) || 90.0} / 100</span>
        </div>
        <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
          <span className="text-gray-500 block">Brightness</span>
          <span className="text-base font-bold text-emerald-900">{cv.brightness?.toFixed(1) || 80.0} / 100</span>
        </div>
        <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
          <span className="text-gray-500 block">Defect Coverage</span>
          <span className="text-base font-bold text-emerald-900">{cv.defect_coverage_percent?.toFixed(2) || 1.5}%</span>
        </div>
      </div>

      {probs.fresh !== undefined && (
        <div>
          <span className="text-xs font-semibold text-gray-600 block mb-1.5">Classifier Confidence Probabilities:</span>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between text-gray-600">
              <span>Fresh Produce:</span>
              <span className="font-semibold">{(probs.fresh * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
              <div className="bg-emerald-500 h-full" style={{ width: `${probs.fresh * 100}%` }}></div>
            </div>

            <div className="flex justify-between text-gray-600 pt-1">
              <span>Minor Defect:</span>
              <span className="font-semibold">{(probs.minor_defect * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
              <div className="bg-amber-500 h-full" style={{ width: `${probs.minor_defect * 100}%` }}></div>
            </div>

            <div className="flex justify-between text-gray-600 pt-1">
              <span>Major Defect:</span>
              <span className="font-semibold">{(probs.major_defect * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
              <div className="bg-red-500 h-full" style={{ width: `${probs.major_defect * 100}%` }}></div>
            </div>
          </div>
        </div>
      )}

      {inspection.defects_detected && inspection.defects_detected.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900">
          <span className="font-bold">Detected Defects: </span>
          {inspection.defects_detected.join(', ')}
        </div>
      )}
    </div>
  );
};

export default CVBreakdownPanel;
