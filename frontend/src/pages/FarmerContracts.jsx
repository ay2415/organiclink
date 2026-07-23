import React, { useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { FileText, Plus, AlertTriangle, Trash2, Calendar } from 'lucide-react';

const FarmerContracts = () => {
  const { user } = useContext(AuthContext);
  const [contracts, setContracts] = useState([]);
  const [formData, setFormData] = useState({
    contract_name: 'Annual Processor Offtake',
    hub_name: 'Bandon Food Aggregators',
    product_type: 'onion',
    committed_quantity: 80,
    quantity_unit: 'kg',
    period: 'month',
    price_per_unit: 1.80,
    status: 'active',
    start_date: '2026-01-01',
    end_date: '2026-12-31'
  });

  useEffect(() => {
    fetchContracts();
  }, []);

  const fetchContracts = async () => {
    const farmId = user?.farm?.id || 'cork-farm-id';
    try {
      const res = await api.get(`/api/farms/${farmId}/contracts`);
      setContracts(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const farmId = user?.farm?.id || 'cork-farm-id';
    try {
      await api.post(`/api/farms/${farmId}/contracts`, formData);
      fetchContracts();
    } catch (err) {
      alert('Error creating contract');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this contract?")) return;
    try {
      await api.delete(`/api/contracts/${id}`);
      fetchContracts();
    } catch (err) {
      alert('Error deleting contract');
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="border-b pb-4">
        <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
          <FileText className="w-6 h-6 text-emerald-700" /> Processor & Manufacturer Contracts
        </h1>
        <p className="text-xs text-gray-500">Fixed committed volumes subtracted automatically from yield to determine surplus (A2 requirement)</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl border border-emerald-100 shadow-sm grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div>
          <label className="font-bold text-gray-700 block mb-1">Contract Name</label>
          <input type="text" value={formData.contract_name} onChange={e=>setFormData({...formData, contract_name: e.target.value})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Processor / Hub</label>
          <input type="text" value={formData.hub_name} onChange={e=>setFormData({...formData, hub_name: e.target.value})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Product</label>
          <select value={formData.product_type} onChange={e=>setFormData({...formData, product_type: e.target.value})} className="w-full border p-2 rounded-lg">
            <option value="onion">Onion</option>
            <option value="milk">Milk</option>
            <option value="apple">Apple</option>
            <option value="potato">Potato</option>
          </select>
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Committed Qty</label>
          <input type="number" value={formData.committed_quantity} onChange={e=>setFormData({...formData, committed_quantity: parseFloat(e.target.value)})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Unit Price (€)</label>
          <input type="number" step="0.10" value={formData.price_per_unit} onChange={e=>setFormData({...formData, price_per_unit: parseFloat(e.target.value)})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">Start Date</label>
          <input type="date" value={formData.start_date} onChange={e=>setFormData({...formData, start_date: e.target.value})} className="w-full border p-2 rounded-lg" />
        </div>
        <div>
          <label className="font-bold text-gray-700 block mb-1">End Date</label>
          <input type="date" value={formData.end_date} onChange={e=>setFormData({...formData, end_date: e.target.value})} className="w-full border p-2 rounded-lg" />
        </div>
        <div className="flex items-end">
          <button type="submit" className="w-full bg-emerald-700 text-white font-bold py-2.5 px-4 rounded-lg hover:bg-emerald-800 flex items-center justify-center gap-1">
            <Plus className="w-4 h-4" /> Save Contract
          </button>
        </div>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {contracts.map((c) => {
          const isExpired = c.status === 'expired' || (c.days_remaining !== null && c.days_remaining <= 0);
          const isExpiringSoon = c.days_remaining !== null && c.days_remaining > 0 && c.days_remaining <= 30;

          return (
            <div key={c.id} className={`bg-white p-5 rounded-2xl border ${isExpired ? 'border-red-300 bg-red-50/20' : 'border-gray-200'} shadow-sm space-y-3`}>
              <div className="flex justify-between items-start">
                <div>
                  <span className="font-extrabold text-gray-900 text-base block">{c.contract_name}</span>
                  <span className="text-xs text-gray-500">Processor: <strong className="text-gray-800">{c.hub_name}</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${isExpired ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-emerald-100 text-emerald-800 border border-emerald-300'}`}>
                    {isExpired ? 'Expired' : c.status}
                  </span>
                  <button onClick={() => handleDelete(c.id)} className="text-gray-400 hover:text-red-600 p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {isExpiringSoon && (
                <div className="bg-amber-50 border border-amber-300 text-amber-900 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  Warning: Contract expiring in {c.days_remaining} days!
                </div>
              )}

              <div className="bg-emerald-50 p-3 rounded-xl border border-emerald-100 flex justify-between items-center text-xs">
                <div>
                  <span className="text-gray-500 block">Committed Volume</span>
                  <span className="font-extrabold text-emerald-900 text-sm">{c.committed_quantity} {c.quantity_unit} / {c.period}</span>
                </div>
                <div className="text-right">
                  <span className="text-gray-500 block">Contract Rate</span>
                  <span className="font-bold text-gray-900">€{c.price_per_unit.toFixed(2)} / {c.quantity_unit}</span>
                </div>
              </div>

              {(c.start_date || c.end_date) && (
                <div className="text-[11px] text-gray-500 flex items-center justify-between border-t pt-2">
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5 text-gray-400" /> Start: {c.start_date || 'N/A'}</span>
                  <span>End: {c.end_date || 'N/A'}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FarmerContracts;
