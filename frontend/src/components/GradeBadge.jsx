import React from 'react';

const GradeBadge = ({ grade, score }) => {
  const getStyle = (g) => {
    switch (g) {
      case 'A': return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'B': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'C': return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'R': return 'bg-red-100 text-red-800 border-red-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${getStyle(grade)}`}>
      GRADE {grade} {score !== undefined && `(${score.toFixed(1)}/100)`}
    </span>
  );
};

export default GradeBadge;
