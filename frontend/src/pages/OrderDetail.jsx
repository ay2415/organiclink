import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import GradeBadge from '../components/GradeBadge';
import VarianceBadge from '../components/VarianceBadge';
import CVBreakdownPanel from '../components/CVBreakdownPanel';
import {
  Upload, CheckCircle2, AlertTriangle, FileText, Star, Truck, ArrowRight, ShieldCheck
} from 'lucide-react';

const OrderDetail = () => {
  const { id } = useParams();
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);

  // Actions state
  const [farmImageFile, setFarmImageFile] = useState(null);
  const [delivImageFile, setDelivImageFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Negotiation state
  const [negPrice, setNegPrice] = useState(0);
  const [negQty, setNegQty] = useState(0);
  const [negMsg, setNegMsg] = useState('');

  // Rating state
  const [stars, setStars] = useState(5);
  const [reviewText, setReviewText] = useState('');

  useEffect(() => {
    fetchOrderDetail();
  }, [id]);

  const fetchOrderDetail = async () => {
    try {
      const res = await api.get(`/api/orders/${id}`);
      setOrder(res.data);
      setNegPrice(res.data.price_per_unit);
      setNegQty(res.data.quantity);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFarmerAccept = async () => {
    try {
      await api.put(`/api/orders/${id}/accept`);
      fetchOrderDetail();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error accepting order');
    }
  };

  const handleFarmerNegotiate = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/api/orders/${id}/negotiate`, {
        quantity: negQty,
        price_per_unit: negPrice,
        message: negMsg
      });
      fetchOrderDetail();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error sending counter offer');
    }
  };

  const handleUploadFarmPhoto = async (e) => {
    e.preventDefault();
    if (!farmImageFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('image', farmImageFile);
      await api.post(`/api/orders/${id}/farm-photo`, formData);
      fetchOrderDetail();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error uploading farm photo');
    } finally {
      setUploading(false);
    }
  };

  const handleDispatch = async () => {
    try {
      await api.put(`/api/orders/${id}/dispatch`);
      fetchOrderDetail();
    } catch (err) {
      alert(err.response?.data?.detail || 'Dispatch rejected');
    }
  };

  const handleUploadDeliveryPhoto = async (e) => {
    e.preventDefault();
    if (!delivImageFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('image', delivImageFile);
      await api.post(`/api/orders/${id}/delivery-photo`, formData);
      fetchOrderDetail();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error uploading delivery photo');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmitRating = async (e) => {
    e.preventDefault();
    try {
      const rateeId = user.id === order.farmer_id ? order.buyer_id : order.farmer_id;
      await api.post('/api/ratings', {
        order_id: id,
        ratee_id: rateeId,
        rating_stars: stars,
        review_text: reviewText
      });
      fetchOrderDetail();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error submitting rating');
    }
  };

  if (loading || !order) {
    return <div className="p-12 text-center text-emerald-800 font-bold">Loading Order Detail...</div>;
  }

  const isFarmer = user?.id === order.farmer_id || user?.role === 'farmer';
  const isBuyer = user?.id === order.buyer_id || user?.role !== 'farmer' && user?.role !== 'admin';

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Order Header */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-gray-900">Order #{order.id.substring(0, 8)}</h1>
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${order.status === 'disputed' ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-emerald-100 text-emerald-800 border border-emerald-300'}`}>
              {order.status}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Organic {order.product_type} ({order.quantity} {order.quantity_unit}) | Total: <span className="font-extrabold text-emerald-800">€{order.total_price.toFixed(2)}</span>
          </p>
        </div>

        {order.invoice_url && (
          <a
            href={order.invoice_url}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 bg-emerald-800 text-white rounded-xl text-xs font-bold flex items-center gap-2 hover:bg-emerald-900 shadow"
          >
            <FileText className="w-4 h-4" /> Download Official Invoice PDF
          </a>
        )}
      </div>

      {/* CENTREPIECE: SIDE-BY-SIDE FARM VS DELIVERY GRADE COMPARISON */}
      <div className="bg-gradient-to-br from-emerald-950 to-emerald-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-emerald-800 pb-4">
          <div>
            <h2 className="text-xl font-extrabold flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-400" /> Farm vs. Delivery Quality Audit & Variance
            </h2>
            <p className="text-xs text-emerald-300">Automated computer vision quality comparison enforcing the ±10% tolerance rule</p>
          </div>

          <VarianceBadge
            variancePercent={order.quality_variance_percent}
            acceptable={order.variance_acceptable}
            isAnomaly={order.quality_variance_percent < -10}
          />
        </div>

        {/* Side-by-Side Images & Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Farm Dispatch Inspection Photo */}
          <div className="bg-emerald-900/60 rounded-2xl p-5 border border-emerald-700/60 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-sm text-emerald-200">1. Farm Dispatch Inspection</h3>
              {order.farm_inspection ? (
                <GradeBadge grade={order.farm_inspection.quality_grade} score={order.farm_inspection.quality_score} />
              ) : (
                <span className="text-xs text-amber-300 font-semibold">Pending Farm Photo</span>
              )}
            </div>

            {order.farm_inspection ? (
              <div className="space-y-3">
                <img src={order.farm_inspection.image_url} alt="Farm Photo" className="w-full h-48 object-cover rounded-xl border border-emerald-700 shadow" />
                <div className="text-xs text-emerald-300 flex justify-between">
                  <span>Inspection Level: Farm Dispatch</span>
                  <span className="font-bold text-white">Score: {order.farm_inspection.quality_score.toFixed(1)}/100</span>
                </div>
              </div>
            ) : isFarmer && (order.status === 'accepted' || order.status === 'pending') ? (
              <form onSubmit={handleUploadFarmPhoto} className="space-y-3 pt-2">
                <input type="file" accept="image/*" onChange={e=>setFarmImageFile(e.target.files[0])} className="text-xs text-emerald-200" />
                <button type="submit" disabled={uploading} className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow">
                  Upload Farm Photo & Run CV
                </button>
              </form>
            ) : (
              <div className="h-48 border border-dashed border-emerald-700 rounded-xl flex items-center justify-center text-xs text-emerald-400">
                Awaiting farmer dispatch photo
              </div>
            )}
          </div>

          {/* Delivery Arrival Inspection Photo */}
          <div className="bg-emerald-900/60 rounded-2xl p-5 border border-emerald-700/60 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-sm text-emerald-200">2. Delivery Arrival Inspection</h3>
              {order.delivery_inspection ? (
                <GradeBadge grade={order.delivery_inspection.quality_grade} score={order.delivery_inspection.quality_score} />
              ) : (
                <span className="text-xs text-amber-300 font-semibold">Pending Delivery Photo</span>
              )}
            </div>

            {order.delivery_inspection ? (
              <div className="space-y-3">
                <img src={order.delivery_inspection.image_url} alt="Delivery Photo" className="w-full h-48 object-cover rounded-xl border border-emerald-700 shadow" />
                <div className="text-xs text-emerald-300 flex justify-between">
                  <span>Inspection Level: Delivery Arrival</span>
                  <span className="font-bold text-white">Score: {order.delivery_inspection.quality_score.toFixed(1)}/100</span>
                </div>
              </div>
            ) : isBuyer && order.status === 'in_transit' ? (
              <form onSubmit={handleUploadDeliveryPhoto} className="space-y-3 pt-2">
                <input type="file" accept="image/*" onChange={e=>setDelivImageFile(e.target.files[0])} className="text-xs text-emerald-200" />
                <button type="submit" disabled={uploading} className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow">
                  Upload Delivery Photo & Verify Variance
                </button>
              </form>
            ) : (
              <div className="h-48 border border-dashed border-emerald-700 rounded-xl flex items-center justify-center text-xs text-emerald-400">
                Awaiting delivery arrival photo from buyer
              </div>
            )}
          </div>
        </div>
      </div>

      {/* State Machine Actions & Timeline */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
        <h3 className="font-bold text-gray-900 text-sm border-b pb-2">Order State Machine & Bank Settlement Controls</h3>

        {/* Bank Settlement Notice (A9) */}
        <div className="bg-blue-50 border border-blue-200 p-3 rounded-xl text-xs text-blue-900 font-medium">
          <strong>Bank Transfer Settlement:</strong> Payments are made directly between buyer and farmer by bank transfer. This platform records status only.
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {isFarmer && (order.status === 'pending' || order.status === 'negotiating') && (
            <button onClick={handleFarmerAccept} className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold">
              Accept Order
            </button>
          )}

          {isFarmer && (order.status === 'accepted' || order.status === 'quality_verified') && (
            <button onClick={handleDispatch} className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-lg text-xs font-bold flex items-center gap-1">
              <Truck className="w-4 h-4" /> Dispatch Order to Transit
            </button>
          )}

          {/* Two-step Payment Confirmation (A9) */}
          {isBuyer && (order.status === 'delivered' || order.status === 'quality_verified') && order.buyer_payment_status !== 'sent' && (
            <button
              onClick={async () => {
                const ref = prompt("Enter Bank Transfer Reference (optional):", "BANK-TRANSFER-01");
                if (ref !== null) {
                  await api.post(`/api/orders/${id}/payment/send`, `payment_reference=${encodeURIComponent(ref)}`, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                  });
                  fetchOrderDetail();
                }
              }}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold shadow"
            >
              Mark Bank Transfer Sent
            </button>
          )}

          {isFarmer && (order.status === 'delivered' || order.buyer_payment_status === 'sent') && order.status !== 'paid' && (
            <button
              onClick={async () => {
                await api.post(`/api/orders/${id}/payment/receive`);
                fetchOrderDetail();
              }}
              className="px-4 py-2 bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg text-xs font-bold shadow"
            >
              Confirm Bank Transfer Received (Mark Paid)
            </button>
          )}
        </div>
      </div>

      {/* Rating & Review Form */}
      {(order.status === 'delivered' || order.status === 'paid' || order.status === 'completed') && (
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-bold text-gray-900 text-sm border-b pb-2">Submit Transaction Rating & Review</h3>
          <form onSubmit={handleSubmitRating} className="space-y-3">
            <div>
              <label className="text-xs font-bold text-gray-700 block mb-1">Rating Stars (1 - 5)</label>
              <select value={stars} onChange={e=>setStars(parseInt(e.target.value))} className="border p-2 rounded-lg text-xs font-bold">
                <option value="5">5 Stars — Excellent</option>
                <option value="4">4 Stars — Good</option>
                <option value="3">3 Stars — Average</option>
                <option value="2">2 Stars — Poor</option>
                <option value="1">1 Star — Unacceptable</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-gray-700 block mb-1">Review Comments</label>
              <textarea value={reviewText} onChange={e=>setReviewText(e.target.value)} rows="2" className="w-full border p-2 rounded-lg text-xs" placeholder="Describe quality consistency, timeliness, and communication..."></textarea>
            </div>
            <button type="submit" className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-lg flex items-center gap-1">
              <Star className="w-4 h-4" /> Submit Review
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default OrderDetail;
