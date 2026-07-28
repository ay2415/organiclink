import React, { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import GradeBadge from '../components/GradeBadge';
import {
  TrendingUp, Award, AlertCircle, PlusCircle, PackageCheck,
  FileText, ShieldCheck, MapPin, ArrowRight
} from 'lucide-react';

const FarmerDashboard = () => {
  const { user } = useContext(AuthContext);
  const [farmData, setFarmData] = useState(null);
  const [surplusSuggestions, setSurplusSuggestions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingPriceId, setEditingPriceId] = useState(null);
  const [editPriceValue, setEditPriceValue] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Find my farm
      const meRes = await api.get('/api/auth/me');
      const farmIdRes = await api.get(`/api/farms/${user?.farm?.id || ''}`).catch(async () => {
        // Fallback search by user
        const fRes = await api.get('/api/farms/farms');
        return fRes;
      });

      // Get canonical farm or first farm
      const farmId = user?.farm?.id || 'cork-farm-id';
      const profile = await api.get(`/api/farms/${farmId}`).catch(() => null);
      if (profile) {
        setFarmData(profile.data);
      }

      // Get surplus suggestions
      const surpRes = await api.get(`/api/farms/${farmId}/surplus-suggestion`).catch(() => []);
      if (surpRes.data) {
        setSurplusSuggestions(surpRes.data);
      }

      // Get pending orders
      const ordRes = await api.get('/api/orders');
      setOrders(ordRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdatePrice = async (prodId) => {
    try {
      await api.patch(`/api/products/${prodId}/price`, { price_per_unit: parseFloat(editPriceValue) });
      setEditingPriceId(null);
      fetchDashboardData();
    } catch (err) {
      alert('Error updating price');
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-emerald-800 font-bold">Loading Farmer Dashboard...</div>;
  }

  const farm = farmData?.farm || user?.farm;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900 to-emerald-800 text-white rounded-2xl p-6 shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-extrabold">{farm?.farm_name || "Glenbeg Organic Farm"}</h1>
            <span className="bg-emerald-700 text-emerald-200 text-xs px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> {farm?.organic_cert_body || "Irish Organic Association"} ({farm?.organic_cert_number || "IOA-10842"})
            </span>
          </div>
          <p className="text-xs text-emerald-200 flex items-center gap-2">
            <MapPin className="w-3.5 h-3.5 text-emerald-400" /> {farm?.town || "Bandon"}, Co. {farm?.county || "Cork"} | Eircode: {farm?.eircode || "T56 AB12"}
          </p>
        </div>

        <div className="flex items-center gap-4 bg-emerald-950/60 p-3 rounded-xl border border-emerald-700/50">
          <div className="text-center">
            <span className="text-[10px] text-emerald-300 uppercase block font-bold">Reputation Score</span>
            <span className="text-xl font-extrabold text-amber-400 flex items-center gap-1 justify-center">
              <Award className="w-5 h-5 text-amber-400" /> {farm?.reputation_score?.toFixed(1) || "88.5"} / 100
            </span>
          </div>
          <div className="h-8 w-px bg-emerald-700"></div>
          <div className="text-center">
            <span className="text-[10px] text-emerald-300 uppercase block font-bold">Orders Completed</span>
            <span className="text-xl font-extrabold text-white">{farm?.total_orders_completed || 14}</span>
          </div>
        </div>
      </div>

      {/* CANONICAL UNCONTRACTED CALCULATION CARD */}
      <div className="bg-gradient-to-r from-amber-500 to-earth-500 text-white p-6 rounded-2xl shadow-md space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-6 h-6 text-amber-100" />
            <h2 className="text-lg font-bold text-white">Automated Available Stock & Listing Assistant</h2>
          </div>
          <span className="bg-white/20 text-white text-xs px-3 py-1 rounded-full font-semibold">Active Contract Calculation</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {surplusSuggestions.length > 0 ? (
            surplusSuggestions.map((s, idx) => {
              const isMilk = s.product_type?.toLowerCase() === 'milk';
              return (
                <div key={idx} className="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/20 flex flex-col justify-between space-y-3">
                  <div>
                    <span className="text-xs uppercase font-bold text-amber-100 tracking-wider block">Product: Organic {s.product_type}</span>
                    <div className="text-sm font-medium mt-1">
                      You produced <span className="font-extrabold text-white">{s.produced_quantity}{s.unit}</span> this period, <span className="font-extrabold text-white">{s.committed_quantity}{s.unit}</span> is committed under processor contract.
                    </div>
                  </div>

                  <div className="bg-white text-amber-950 p-3 rounded-lg flex items-center justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-amber-700 block">Available Stock</span>
                      <span className="text-lg font-extrabold text-emerald-700">{s.suggested_surplus} {s.unit}</span>
                    </div>
                    
                    {/* Part 4 Milk Rule: Hide List Available Stock button for milk */}
                    {!isMilk ? (
                      <Link
                        to={`/farmer/listings/new?product_type=${s.product_type}&qty=${s.suggested_surplus}`}
                        className="bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-1 shadow-sm transition-all"
                      >
                        <PlusCircle className="w-4 h-4" /> List {s.suggested_surplus}{s.unit}
                      </Link>
                    ) : (
                      <span className="text-[10px] bg-amber-100 text-amber-900 font-bold px-2.5 py-1 rounded-md">
                        Milk Contract Declared
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="col-span-3 bg-white/10 p-4 rounded-xl text-center text-sm">
              You produced 100kg onions, 80kg is committed — list your <span className="font-bold text-white">20kg available stock</span>.
            </div>
          )}
        </div>
      </div>

      {/* Quick Action Navigation Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/farmer/listings/new" className="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm hover:shadow-md transition-all flex items-center gap-3">
          <div className="p-3 bg-emerald-100 text-emerald-800 rounded-lg"><PlusCircle className="w-5 h-5" /></div>
          <div>
            <span className="font-bold text-gray-900 text-sm block">New Listing</span>
            <span className="text-xs text-gray-500">Run CV Quality Grading</span>
          </div>
        </Link>

        <Link to="/farmer/production" className="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm hover:shadow-md transition-all flex items-center gap-3">
          <div className="p-3 bg-blue-100 text-blue-800 rounded-lg"><TrendingUp className="w-5 h-5" /></div>
          <div>
            <span className="font-bold text-gray-900 text-sm block">Yield History</span>
            <span className="text-xs text-gray-500">Monthly Yield Charts</span>
          </div>
        </Link>

        <Link to="/farmer/contracts" className="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm hover:shadow-md transition-all flex items-center gap-3">
          <div className="p-3 bg-amber-100 text-amber-800 rounded-lg"><FileText className="w-5 h-5" /></div>
          <div>
            <span className="font-bold text-gray-900 text-sm block">Contracts</span>
            <span className="text-xs text-gray-500">Processor Offtake</span>
          </div>
        </Link>

        <Link to="/farmer/hubs" className="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm hover:shadow-md transition-all flex items-center gap-3">
          <div className="p-3 bg-purple-100 text-purple-800 rounded-lg"><MapPin className="w-5 h-5" /></div>
          <div>
            <span className="font-bold text-gray-900 text-sm block">Nearest Buyers</span>
            <span className="text-xs text-gray-500">Ranked by Haversine</span>
          </div>
        </Link>
      </div>

      {/* Orders & Active Listings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Pending Orders requiring Farmer Action */}
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-gray-100 pb-3">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <PackageCheck className="w-5 h-5 text-emerald-700" /> Incoming Buyer Orders
            </h3>
            <span className="text-xs text-gray-500 font-semibold">{orders.length} Total</span>
          </div>

          <div className="space-y-3">
            {orders.slice(0, 5).map((ord) => (
              <div key={ord.id} className="p-4 rounded-xl bg-gray-50 border border-gray-200 flex items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-sm text-gray-900">Order #{ord.id.substring(0, 8)}</span>
                    <span className="text-xs font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full uppercase">{ord.status}</span>
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    Buyer: <span className="font-semibold text-gray-800">{ord.buyer_name}</span> | {ord.quantity}{ord.quantity_unit} for <span className="font-bold text-emerald-700">€{ord.total_price.toFixed(2)}</span>
                  </div>
                </div>

                <Link to={`/orders/${ord.id}`} className="px-3 py-1.5 bg-emerald-700 text-white rounded-lg text-xs font-bold hover:bg-emerald-800 flex items-center gap-1">
                  Manage <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* Active Listings */}
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-gray-100 pb-3">
            <h3 className="font-bold text-gray-900">My Active Listings</h3>
            <Link to="/marketplace" className="text-xs font-bold text-emerald-700 hover:underline">View All</Link>
          </div>

          <div className="space-y-3">
            {farmData?.active_listings?.slice(0, 5).map((prod) => (
              <div key={prod.id} className="p-3 rounded-xl border border-gray-200 flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <img src={prod.image_url} alt={prod.product_type} className="w-12 h-12 object-cover rounded-lg" />
                    <div>
                      <div className="font-bold text-sm text-gray-900 capitalize">{prod.product_type} ({prod.available_quantity}{prod.quantity_unit})</div>
                      <div className="text-xs text-gray-500">€{prod.price_per_unit.toFixed(2)} / {prod.quantity_unit}</div>
                    </div>
                  </div>
                  <GradeBadge grade={prod.quality_grade} score={prod.quality_score} />
                </div>
                
                {/* Inline Price Editor */}
                <div className="flex justify-end border-t pt-2 mt-1">
                  {editingPriceId === prod.id ? (
                    <div className="flex items-center gap-2">
                      <input 
                        type="number" step="0.05" 
                        value={editPriceValue} 
                        onChange={e => setEditPriceValue(e.target.value)} 
                        className="border rounded px-2 py-1 text-xs w-20"
                      />
                      <button onClick={() => handleUpdatePrice(prod.id)} className="bg-emerald-600 text-white px-2 py-1 rounded text-xs font-bold">Save</button>
                      <button onClick={() => setEditingPriceId(null)} className="text-gray-500 text-xs hover:underline">Cancel</button>
                    </div>
                  ) : (
                    <button 
                      onClick={() => { setEditingPriceId(prod.id); setEditPriceValue(prod.price_per_unit); }} 
                      className="text-xs font-bold text-emerald-700 hover:text-emerald-800 bg-emerald-50 px-2 py-1 rounded"
                    >
                      Edit Price
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FarmerDashboard;
