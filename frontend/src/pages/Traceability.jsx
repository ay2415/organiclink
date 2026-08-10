import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';
import GradeBadge from '../components/GradeBadge';
import { ShieldCheck, MapPin, CheckCircle2, Award, Calendar, Package, ArrowLeft, QrCode } from 'lucide-react';

const Traceability = () => {
  const { type, id } = useParams(); // type: 'product' or 'order'
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchTraceability();
  }, [type, id]);

  const fetchTraceability = async () => {
    try {
      const endpoint = type === 'order' ? `/api/traceability/order/${id}` : `/api/traceability/product/${id}`;
      const res = await api.get(endpoint);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load traceability record');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-emerald-800 font-bold">Loading Produce Traceability Audit...</div>;
  }

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-red-50 border border-red-200 rounded-2xl text-center space-y-4">
        <h2 className="text-xl font-bold text-red-800">Traceability Record Not Found</h2>
        <p className="text-xs text-red-600">{error}</p>
        <Link to="/marketplace" className="inline-block px-4 py-2 bg-emerald-800 text-white rounded-lg text-xs font-bold">
          Return to Marketplace
        </Link>
      </div>
    );
  }

  const { farm, product, order, inspections } = data;
  const qrUrl = `/api/traceability/qr?url=${encodeURIComponent(window.location.href)}`;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Back Link */}
      <Link to="/marketplace" className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 hover:underline">
        <ArrowLeft className="w-4 h-4" /> Back to Marketplace
      </Link>

      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900 to-emerald-950 text-white rounded-3xl p-6 sm:p-8 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border border-emerald-800">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-800/80 rounded-full text-xs font-bold text-emerald-300 border border-emerald-700">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Official Irish Organic Traceability Passport
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold capitalize">
            {product?.product_type || order?.product_type} Produce Audit
          </h1>
          <p className="text-xs text-emerald-300">
            Verified farm of origin, organic certification status, and computer vision quality inspection history
          </p>
        </div>

        {/* Embedded QR Code */}
        <div className="bg-white p-3 rounded-2xl shadow-lg border border-emerald-200 text-center space-y-1 self-center">
          <img src={qrUrl} alt="Traceability QR Code" className="w-28 h-28 mx-auto" />
          <span className="text-[10px] font-extrabold text-emerald-900 block uppercase tracking-wider">Scan Passport</span>
        </div>
      </div>

      {/* Grid: Farm of Origin & Organic Certification */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Farm of Origin */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b pb-3 text-emerald-900 font-extrabold text-sm">
            <MapPin className="w-5 h-5 text-emerald-700" /> Farm of Origin
          </div>
          <div className="space-y-2.5 text-xs text-gray-700">
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">Farm Name:</span>
              <span className="font-bold text-gray-900">{farm.farm_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">Location:</span>
              <span className="font-bold text-gray-900">{farm.town}, Co. {farm.county}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">Certified Farmer:</span>
              <span className="font-bold text-gray-900">{farm.farmer_name}</span>
            </div>
          </div>
        </div>

        {/* Organic Certification Status */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b pb-3 text-emerald-900 font-extrabold text-sm">
            <Award className="w-5 h-5 text-emerald-700" /> Organic Certification Status
          </div>
          <div className="space-y-2.5 text-xs text-gray-700">
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">Verification State:</span>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold uppercase bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Verified Organic
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">Control Authority:</span>
              <span className="font-bold text-gray-900">{farm.organic_cert_body || 'IOA'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">License Number:</span>
              <span className="font-mono font-bold text-emerald-800">{farm.organic_cert_number || 'IOA-REG-2026'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quality Inspection Audit History */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
        <h3 className="font-extrabold text-gray-900 text-base border-b pb-3 flex items-center gap-2">
          <Package className="w-5 h-5 text-emerald-700" /> Complete Quality Inspection & Dispatch Passport
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Farm Listing Inspection */}
          {inspections.listing_inspection && (
            <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-xs text-emerald-900">1. Listing Inspection</span>
                <GradeBadge grade={inspections.listing_inspection.grade} score={inspections.listing_inspection.score} />
              </div>
              <div className="text-[11px] text-emerald-800 space-y-1">
                <div>Score: <strong>{inspections.listing_inspection.score ? `${inspections.listing_inspection.score.toFixed(1)}/100` : 'N/A'}</strong></div>
                <div className="text-gray-500 text-[10px]">Harvest & Initial Grade</div>
              </div>
              {inspections.listing_inspection.image_url && (
                <img src={inspections.listing_inspection.image_url} alt="Listing Photo" className="w-full h-28 object-cover rounded-lg border border-emerald-200 mt-2" />
              )}
            </div>
          )}

          {/* Farm Dispatch Inspection & Recipient Details */}
          <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-xs text-emerald-900">2. Dispatch & Recipient</span>
              {inspections.farm_dispatch?.grade ? (
                <GradeBadge grade={inspections.farm_dispatch.grade} score={inspections.farm_dispatch.score} />
              ) : (
                <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded-full uppercase">Pending Dispatch</span>
              )}
            </div>
            <div className="text-[11px] text-emerald-900 space-y-1">
              <div>Dispatch Date: <strong>{data.dispatch?.dispatch_date || inspections.farm_dispatch?.created_at || 'Awaiting Transit'}</strong></div>
              <div>Dispatched To (Buyer): <strong>{data.dispatch?.recipient_name || data.recipient?.name || data.buyer?.name || 'Assigned Buyer'}</strong> ({data.dispatch?.recipient_role || data.recipient?.role || 'buyer'})</div>
              {inspections.farm_dispatch?.score && (
                <div>Dispatch Score: <strong>{inspections.farm_dispatch.score.toFixed(1)}/100</strong></div>
              )}
            </div>
            {inspections.farm_dispatch?.image_url && (
              <img src={inspections.farm_dispatch.image_url} alt="Dispatch Photo" className="w-full h-28 object-cover rounded-lg border border-emerald-200 mt-2" />
            )}
          </div>

          {/* Delivery Arrival Inspection */}
          <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-xs text-emerald-900">3. Delivery Arrival Audit</span>
              {inspections.delivery_arrival?.grade ? (
                <GradeBadge grade={inspections.delivery_arrival.grade} score={inspections.delivery_arrival.score} />
              ) : (
                <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded-full uppercase">Pending Arrival</span>
              )}
            </div>
            <div className="text-[11px] text-emerald-900 space-y-1">
              <div>Delivery Date: <strong>{data.delivery?.delivery_date || inspections.delivery_arrival?.created_at || 'In Transit'}</strong></div>
              {inspections.delivery_arrival?.score ? (
                <div>Arrival Score: <strong>{inspections.delivery_arrival.score.toFixed(1)}/100</strong></div>
              ) : (
                <div className="text-gray-500 text-[10px]">Awaiting buyer delivery verification</div>
              )}
            </div>
            {inspections.delivery_arrival?.image_url && (
              <img src={inspections.delivery_arrival.image_url} alt="Delivery Photo" className="w-full h-28 object-cover rounded-lg border border-emerald-200 mt-2" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Traceability;
