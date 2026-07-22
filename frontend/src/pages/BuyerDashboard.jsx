import React, { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { ShoppingBag, ArrowRight } from 'lucide-react';

const BuyerDashboard = () => {
  const { user } = useContext(AuthContext);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const res = await api.get('/api/orders');
      setOrders(res.data || []);
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
          <ShoppingBag className="w-6 h-6 text-emerald-700" /> Buyer Order Portal
        </h1>
        <p className="text-xs text-gray-500">Manage orders, upload delivery quality photos, verify quality variance, and download PDF invoices</p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-emerald-50 text-emerald-950 uppercase font-bold border-b">
            <tr>
              <th className="p-3">Order ID</th>
              <th className="p-3">Farm Name</th>
              <th className="p-3">Product Type</th>
              <th className="p-3">Quantity</th>
              <th className="p-3">Total Price (€)</th>
              <th className="p-3">Status</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {orders.map((ord) => (
              <tr key={ord.id} className="hover:bg-gray-50">
                <td className="p-3 font-mono font-bold text-emerald-800">#{ord.id.substring(0, 8)}</td>
                <td className="p-3 font-semibold text-gray-900">{ord.farm_name}</td>
                <td className="p-3 capitalize font-bold">{ord.product_type}</td>
                <td className="p-3">{ord.quantity} {ord.quantity_unit}</td>
                <td className="p-3 font-extrabold text-emerald-700">€{ord.total_price.toFixed(2)}</td>
                <td className="p-3">
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${ord.status === 'disputed' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'}`}>
                    {ord.status}
                  </span>
                </td>
                <td className="p-3">
                  <Link to={`/orders/${ord.id}`} className="px-3 py-1 bg-emerald-700 text-white rounded text-xs font-bold hover:bg-emerald-800 inline-flex items-center gap-1">
                    Manage <ArrowRight className="w-3 h-3" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BuyerDashboard;
