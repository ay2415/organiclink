import React, { useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { TrendingUp, Plus, Calendar, PackageCheck, AlertCircle } from 'lucide-react';

const FarmerProduction = () => {
  const { user } = useContext(AuthContext);
  const [logs, setLogs] = useState([]);
  const [surplusData, setSurplusData] = useState(null);

  // Form states
  const [productType, setProductType] = useState('milk');
  const [logType, setLogType] = useState('daily'); // daily vs batch
  const [logDate, setLogDate] = useState(new Date().toISOString().split('T')[0]);
  const [batchRef, setBatchRef] = useState('');
  const [quantity, setQuantity] = useState(100);
  const [unit, setUnit] = useState('litre');

  useEffect(() => {
    fetchLogs();
    fetchSurplus();
  }, [productType]);

  const fetchLogs = async () => {
    try {
      const res = await api.get(`/api/production-logs?product_type=${productType}`);
      setLogs(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchSurplus = async () => {
    try {
      const res = await api.get(`/api/production-logs/surplus?product_type=${productType}`);
      setSurplusData(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/production-logs', {
        product_type: productType,
        log_type: logType,
        log_date: logDate,
        batch_reference: logType === 'batch' ? batchRef : null,
        quantity: parseFloat(quantity),
        unit: unit,
        notes: logType === 'daily' ? 'Day-wise milk entry' : 'Batch harvest log'
      });
      fetchLogs();
      fetchSurplus();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error saving production log');
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-emerald-700" /> Production & Yield Logging (Addendum A3)
          </h1>
          <p className="text-xs text-gray-500">Day-wise logging for Milk & Liquid Dairy | Batch-wise logging for Produce & Crops</p>
        </div>
      </div>

      {/* Surplus Calculation Assistant Banner */}
      {surplusData && (
        <div className="bg-gradient-to-r from-emerald-900 to-emerald-800 text-white p-5 rounded-2xl shadow-md flex justify-between items-center gap-4">
          <div>
            <span className="text-[11px] uppercase tracking-wider text-emerald-300 font-bold block">Surplus Calculation Engine</span>
            <h3 className="text-lg font-bold capitalize">Organic {surplusData.product_type}</h3>
            <p className="text-xs text-emerald-200 mt-0.5">
              Produced: <strong>{surplusData.total_produced} {surplusData.unit}</strong> | Active Contracts: <strong>{surplusData.total_committed} {surplusData.unit}</strong>
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-md px-4 py-2 rounded-xl text-center border border-white/20">
            <span className="text-[10px] text-emerald-200 uppercase font-bold block">Uncontracted Surplus</span>
            <span className="text-xl font-extrabold text-amber-300">{surplusData.surplus} {surplusData.unit}</span>
          </div>
        </div>
      )}

      {/* Logging Entry Form */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl border border-emerald-100 shadow-sm space-y-4 text-xs">
        <h3 className="font-bold text-gray-900 text-sm border-b pb-2 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-emerald-700" /> Log Production Volume
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <label className="font-bold text-gray-700 block mb-1">Product Type</label>
            <select
              value={productType}
              onChange={e => {
                const val = e.target.value;
                setProductType(val);
                if (val === 'milk') {
                  setLogType('daily');
                  setUnit('litre');
                } else {
                  setLogType('batch');
                  setUnit('kg');
                }
              }}
              className="w-full border p-2 rounded-lg font-semibold"
            >
              <option value="milk">Milk (Liquid Dairy)</option>
              <option value="onion">Onion (Produce)</option>
              <option value="apple">Apple (Fruit)</option>
              <option value="potato">Potato (Crops)</option>
              <option value="carrot">Carrot (Crops)</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-gray-700 block mb-1">Log Pattern</label>
            <select value={logType} onChange={e=>setLogType(e.target.value)} className="w-full border p-2 rounded-lg font-semibold">
              <option value="daily">Day-wise Daily Entry (Milk/Dairy)</option>
              <option value="batch">Batch-wise Harvest Entry (Produce)</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-gray-700 block mb-1">Log Date</label>
            <input type="date" value={logDate} onChange={e=>setLogDate(e.target.value)} className="w-full border p-2 rounded-lg" />
          </div>

          {logType === 'batch' ? (
            <div>
              <label className="font-bold text-gray-700 block mb-1">Batch Reference</label>
              <input
                type="text"
                placeholder="e.g. ONION-20260723-A"
                value={batchRef}
                onChange={e=>setBatchRef(e.target.value)}
                className="w-full border p-2 rounded-lg font-mono"
              />
            </div>
          ) : (
            <div>
              <label className="font-bold text-gray-700 block mb-1">Quantity Volume ({unit})</label>
              <input type="number" step="0.1" value={quantity} onChange={e=>setQuantity(parseFloat(e.target.value))} className="w-full border p-2 rounded-lg" />
            </div>
          )}
        </div>

        {logType === 'batch' && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="font-bold text-gray-700 block mb-1">Harvested Quantity ({unit})</label>
              <input type="number" step="0.1" value={quantity} onChange={e=>setQuantity(parseFloat(e.target.value))} className="w-full border p-2 rounded-lg" />
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2">
          <button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-2.5 px-6 rounded-lg flex items-center gap-1 shadow">
            <Plus className="w-4 h-4" /> Save Production Log
          </button>
        </div>
      </form>

      {/* Production Logs Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden space-y-2">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-gray-900 text-sm">Recorded Logs for Organic {productType}</h3>
          <span className="text-xs text-gray-500 font-semibold">{logs.length} Log Entries</span>
        </div>

        <table className="w-full text-left text-xs">
          <thead className="bg-gray-50 text-gray-700 uppercase font-bold border-b">
            <tr>
              <th className="p-3">Log Date</th>
              <th className="p-3">Pattern</th>
              <th className="p-3">Batch Reference</th>
              <th className="p-3">Quantity</th>
              <th className="p-3">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {logs.map((row) => (
              <tr key={row.id} className="hover:bg-gray-50">
                <td className="p-3 font-bold text-gray-900">{row.log_date}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${row.log_type === 'daily' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'}`}>
                    {row.log_type}
                  </span>
                </td>
                <td className="p-3 font-mono text-gray-600">{row.batch_reference || 'N/A'}</td>
                <td className="p-3 font-extrabold text-emerald-800">{row.quantity} {row.unit}</td>
                <td className="p-3 text-gray-500">{row.notes || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default FarmerProduction;
