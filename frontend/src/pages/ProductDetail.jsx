import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import GradeBadge from '../components/GradeBadge';
import CVBreakdownPanel from '../components/CVBreakdownPanel';
import {
  MapPin, ShieldCheck, Download, Award, ShoppingCart, MessageSquare,
  TrendingUp, Truck, AlertCircle
} from 'lucide-react';

const ProductDetail = () => {
  const { id } = useParams();
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [orderQty, setOrderQty] = useState(10.0);
  const [deliveryAddress, setDeliveryAddress] = useState('Cork, Ireland');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchProduct();
  }, [id]);

  const fetchProduct = async () => {
    try {
      const res = await api.get(`/api/products/${id}`);
      setData(res.data);
      if (res.data.product) {
        setOrderQty(Math.min(10.0, res.data.product.available_quantity));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const [deliveryType, setDeliveryType] = useState('direct'); // direct, collection_point
  const [collectionPoint, setCollectionPoint] = useState('');
  const [hubs, setHubs] = useState([]);

  useEffect(() => {
    if (data?.farm?.county) {
      api.get(`/api/hubs/collection-points?county=${encodeURIComponent(data.farm.county)}`)
        .then(res => {
          setHubs(res.data || []);
          if (res.data && res.data.length > 0) {
            setCollectionPoint(res.data[0].name);
          }
        })
        .catch(err => console.error(err));
    }
  }, [data]);

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (!user) {
      navigate('/login');
      return;
    }
    setSubmitting(true);

    try {
      const orderRes = await api.post('/api/orders', {
        product_id: id,
        quantity: orderQty,
        delivery_date: new Date(Date.now() + 86400000 * 2).toISOString().split('T')[0],
        delivery_address: deliveryType === 'collection_point' ? `Collection Point: ${collectionPoint}` : deliveryAddress,
        delivery_type: deliveryType,
        collection_point_name: deliveryType === 'collection_point' ? collectionPoint : null,
        transport_by: 'farmer'
      });
      navigate(`/orders/${orderRes.data.id}`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to place order.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !data) {
    return <div className="p-12 text-center text-emerald-800 font-bold">Loading Product Quality Details...</div>;
  }

  const { product, farm, farmer, inspection, certificate_url, demand } = data;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Breadcrumb & Header */}
      <div className="flex justify-between items-center border-b pb-4">
        <div>
          <Link to="/marketplace" className="text-xs font-bold text-emerald-700 hover:underline">← Back to Marketplace</Link>
          <h1 className="text-3xl font-extrabold text-gray-900 capitalize mt-1">Organic {product.product_type}</h1>
          <p className="text-xs text-gray-500">Listed by {farm?.farm_name} ({farm?.town}, Co. {farm?.county})</p>
        </div>
        <GradeBadge grade={product.quality_grade} score={product.quality_score} />
      </div>

      {/* Main Grid: Image + Order Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Main Image */}
          <div className="relative rounded-2xl overflow-hidden border border-gray-200 shadow-md max-h-96">
            <img src={product.image_url} alt={product.product_type} className="w-full h-full object-cover" />
            <div className="absolute top-4 left-4 bg-emerald-950/80 text-white text-xs font-bold px-3 py-1.5 rounded-full flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> 100% Certified Organic ({farm?.organic_cert_number || "IOA-10842"})
            </div>
          </div>

          {/* DEMAND INDICATOR WIDGET (CRITICAL REQUIREMENT) */}
          <div className="bg-white p-5 rounded-2xl border border-emerald-100 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-100 text-emerald-800 rounded-xl">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-bold text-gray-500 block uppercase">Market Demand Index</span>
                <span className="text-xl font-extrabold text-gray-900">{demand?.demand_score?.toFixed(1)} / 100</span>
              </div>
            </div>

            <div className="text-right">
              {demand?.is_estimate ? (
                <span className="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1 rounded-full border border-amber-200 inline-flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600" /> Seasonal Estimate
                </span>
              ) : (
                <span className="bg-emerald-100 text-emerald-900 text-xs font-bold px-3 py-1 rounded-full border border-emerald-200">
                  Live Activity Based ({demand?.interaction_count} buyer interactions)
                </span>
              )}
            </div>
          </div>

          {/* Bulk Batch Summary Banner */}
          {product.is_bulk && product.bulk_summary && (
            <div className="bg-gradient-to-r from-amber-500 to-emerald-600 text-white p-4 rounded-xl shadow-sm flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-amber-100 block">YOLOv8 Two-Stage Bulk Inspection</span>
                <span className="text-base font-extrabold">{product.bulk_summary}</span>
              </div>
              <span className="bg-white/20 text-white text-xs font-bold px-3 py-1 rounded-full">
                Batch Grade {product.quality_grade}
              </span>
            </div>
          )}

          {/* Computer Vision Full Breakdown Panel */}
          {inspection && (
            <CVBreakdownPanel inspection={inspection} title="Farm Dispatch Computer Vision Analysis" />
          )}

          {/* Certificate Download */}
          {certificate_url && (
            <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 flex items-center justify-between">
              <div>
                <span className="font-bold text-emerald-950 text-sm block">Official Quality Inspection Certificate</span>
                <span className="text-xs text-emerald-700">Formal PDF document generated by ReportLab</span>
              </div>
              <a
                href={certificate_url}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow"
              >
                <Download className="w-4 h-4" /> Download PDF Certificate
              </a>
            </div>
          )}
        </div>

        {/* Purchase Order Card */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-lg h-fit space-y-5">
          <div>
            <span className="text-xs font-bold text-gray-500 uppercase block">Price</span>
            <div className="text-3xl font-extrabold text-emerald-800">
              €{product.price_per_unit.toFixed(2)} <span className="text-sm font-normal text-gray-500">/ {product.quantity_unit}</span>
            </div>
            <span className="text-xs text-gray-500 block mt-1">Available Stock: <span className="font-bold text-gray-800">{product.available_quantity} {product.quantity_unit}</span></span>
          </div>

          {/* Farm Profile Summary */}
          <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-2">
            <Link to={`/farm/${farm?.id}`} className="font-bold text-gray-900 text-sm hover:text-emerald-700 flex items-center justify-between">
              <span>{farm?.farm_name}</span>
              <span className="text-xs text-emerald-700 font-semibold">View Profile →</span>
            </Link>
            <div className="text-xs text-gray-600 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" /> {farm?.town}, Co. {farm?.county}
            </div>
            <div className="text-xs text-amber-700 font-bold flex items-center gap-1">
              <Award className="w-3.5 h-3.5" /> Farmer Reputation: {farmer?.reputation_score?.toFixed(1)} / 100
            </div>
          </div>

          {/* Order Form */}
          <form onSubmit={handlePlaceOrder} className="space-y-4 pt-2">
            <div>
              <label className="text-xs font-bold text-gray-700 block mb-1">Order Quantity ({product.quantity_unit})</label>
              <input
                type="number"
                step="0.5"
                min="1"
                max={product.available_quantity}
                value={orderQty}
                onChange={e=>setOrderQty(parseFloat(e.target.value))}
                className="w-full border p-2.5 rounded-lg text-sm font-bold text-emerald-900"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-gray-700 block mb-2">Delivery / Collection Method</label>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => setDeliveryType('direct')}
                  className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                    deliveryType === 'direct'
                      ? 'bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  🚚 Direct Home Address
                </button>

                <button
                  type="button"
                  onClick={() => setDeliveryType('collection_point')}
                  className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                    deliveryType === 'collection_point'
                      ? 'bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  📍 Local City Hub Pickup
                </button>
              </div>

              {deliveryType === 'direct' ? (
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">Local Address (Co. {farm?.county})</label>
                  <input
                    type="text"
                    value={deliveryAddress}
                    onChange={e=>setDeliveryAddress(e.target.value)}
                    placeholder={`e.g. Grand Parade, ${farm?.town || farm?.county}`}
                    className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                  />
                </div>
              ) : (
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">Select Common City Collection Point</label>
                  <select
                    value={collectionPoint}
                    onChange={e=>setCollectionPoint(e.target.value)}
                    className="w-full border p-2.5 rounded-lg text-xs font-bold text-emerald-900 bg-emerald-50/50"
                  >
                    {hubs.length > 0 ? (
                      hubs.map(h => (
                        <option key={h.id} value={h.name}>
                          {h.name} ({h.town})
                        </option>
                      ))
                    ) : (
                      <option value={`Central ${farm?.county} Farmers Hub`}>
                        Central {farm?.county} Farmers Market Drop-Off Point
                      </option>
                    )}
                  </select>
                  <span className="text-[10px] text-gray-500 block mt-1">
                    Farmer drops off batch at hub. Ideal for individual 10-20kg buyers.
                  </span>
                </div>
              )}
            </div>

            <div className="p-3 bg-emerald-50 rounded-lg text-xs font-bold text-emerald-950 flex justify-between">
              <span>Total Price:</span>
              <span className="text-base text-emerald-800">€{(orderQty * product.price_per_unit).toFixed(2)}</span>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold rounded-xl shadow-md transition-all flex items-center justify-center gap-2 text-sm"
            >
              <ShoppingCart className="w-5 h-5" /> Place Order
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;
