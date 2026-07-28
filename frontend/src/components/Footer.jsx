import React from 'react';
import { Leaf } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-emerald-950 text-emerald-200 border-t border-emerald-900 py-8 mt-16 text-xs">
      <div className="max-w-7xl mx-auto px-4 text-center sm:text-left flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-2">
          <Leaf className="w-4 h-4 text-emerald-400" />
          <span className="font-bold text-white">OrganicLink Ireland</span>
          <span>— Irish Organic Agricultural Marketplace</span>
        </div>
        <div className="text-emerald-400 font-medium">
          Computer Vision Quality Grading | Certified Organic Traceability | EUR Currency & Metric System
        </div>
      </div>
    </footer>
  );
};

export default Footer;
