import React, { useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { TrendingUp, Plus } from 'lucide-react';

const FarmerProduction = () => {
  const { user } = useContext(AuthContext);
  const [history, setHistory] = useState([]);
  const [formData, setFormData] = useState({
    product_type: 'onion',
    year: 2026,
    month: 6,
    quantity: 100,
    unit: 'kg'
  });

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    const farmId = user?.farm?.id || 'cork-farm-id';
    try {
      const res = await api.get(`/api/farms/${farmId}/production`);
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const farmId = user?.farm?.id || 'cork-farm-id';
    try {
      await api.post(`/api/farms/${farmId}/production`, formData);
      fetchHistory();
    } catch (err) {
      alert('Error adding production row');
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-emerald-700" /> Production & Yield History
          </h1>
          <p className="text-xs text-gray-500">Multi-year monthly yield tracker for Irish organic produce & dairy</p>
        </div>
      </div>

      {/* Add Form */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl border border-emerald-100 shadow-sm grid grid-cols-2 sm:grid-cols-5 gap-4 items-end text-xs">
        <div>
          <label className="font-bold text-gray-700 block mb-1">Product Type</label>
          <select value={formData.product_type} onChange={e=>setFormData({...formData, product_type: e.target.value})} className="w-full border p-2 rounded-lg font-semibold">
            <option value="onion">Onion</option>
            <option value="milk">Milk</option>
            <option value="apple">Apple</option>
            <option value="potato">Potato</option>
            <option value="carrot">Carrot</option>
          </select>
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Year</label>
          <input type="number" value={formData.year} onChange={e=>setFormData({...formData, year: parseInt(e.target.value)})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Month (1-12)</label>
          <input type="number" min="1" max="12" value={formData.month} onChange={e=>setFormData({...formData, month: parseInt(e.target.value)})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Quantity</label>
          <input type="number" value={formData.quantity} onChange={e=>setFormData({...formData, quantity: parseFloat(e.target.value)})} className="w-full border p-2 rounded-lg" />
        </div>
        <button type="submit" className="bg-emerald-700 text-white font-bold py-2 px-4 rounded-lg hover:bg-emerald-800 flex items-center justify-center gap-1">
          <Plus className="w-4 h-4" /> Add Record
        </button>
      </form>

      {/* History Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-emerald-50 text-emerald-950 uppercase font-bold border-b">
            <tr>
              <th className="p-3">Year / Month</th>
              <th className="p-3">Product Type</th>
              <th className="p-3">Yield Quantity</th>
              <th className="p-3">Unit</th>
              <th className="p-3">Created Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {history.map((row) => (
              <tr key={row.id} className="hover:bg-gray-50">
                <td className="p-3 font-bold">{row.year} - Month {row.month || 'Annual'}</td>
                <td className="p-3 capitalize font-semibold text-emerald-800">{row.product_type}</td>
                <td className="p-3 font-extrabold">{row.quantity}</td>
                <td className="p-3 uppercase text-gray-500 font-bold">{row.unit}</td>
                <td className="p-3 text-gray-500">{new Date(row.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default FarmerProduction;
