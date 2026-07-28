import React, { useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import GradeBadge from '../components/GradeBadge';
import { Receipt } from 'lucide-react';

const FarmerSalesHistory = () => {
  const { user } = useContext(AuthContext);
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSalesHistory();
  }, []);

  const fetchSalesHistory = async () => {
    const farmId = user?.farm?.id || 'cork-farm-id';
    try {
      const res = await api.get(`/api/farms/${farmId}/sales-history`);
      setSales(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="border-b pb-4">
        <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
          <Receipt className="w-6 h-6 text-emerald-700" /> Completed Sales History
        </h1>
        <p className="text-xs text-gray-500">Historical ledger of delivered produce, buyer roles, prices, and quality grades</p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-emerald-50 text-emerald-950 uppercase font-bold border-b">
            <tr>
              <th className="p-3">Order ID</th>
              <th className="p-3">Product Type</th>
              <th className="p-3">Buyer Name</th>
              <th className="p-3">Buyer Role</th>
              <th className="p-3">Quantity</th>
              <th className="p-3">Final Price (€)</th>
              <th className="p-3">Quality Grade</th>
              <th className="p-3">Sale Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sales.map((s) => (
              <tr key={s.order_id} className="hover:bg-gray-50">
                <td className="p-3 font-mono font-bold text-emerald-800">#{s.order_id.substring(0, 8)}</td>
                <td className="p-3 font-bold capitalize text-gray-900">{s.product_type}</td>
                <td className="p-3 font-semibold text-gray-800">{s.buyer_name}</td>
                <td className="p-3 uppercase text-[10px] font-bold text-gray-500">{s.buyer_role}</td>
                <td className="p-3 font-bold">{s.quantity} {s.quantity_unit}</td>
                <td className="p-3 font-extrabold text-emerald-700">€{s.final_price.toFixed(2)}</td>
                <td className="p-3"><GradeBadge grade={s.quality_grade} score={s.quality_score} /></td>
                <td className="p-3 text-gray-500">{s.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default FarmerSalesHistory;
