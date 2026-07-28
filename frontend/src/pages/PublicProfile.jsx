import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';
import GradeBadge from '../components/GradeBadge';
import { User, MapPin, ShieldCheck, Award, Star, Calendar, ShoppingBag, ArrowLeft } from 'lucide-react';

const PublicProfile = () => {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState('');

  useEffect(() => {
    fetchPublicProfile();
  }, [id]);

  const fetchPublicProfile = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/users/${id}/public`);
      setProfile(res.data);
    } catch (err) {
      console.error(err);
      setErrMsg('Failed to load user profile');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-emerald-800 font-bold">Loading User Profile...</div>;
  }

  if (errMsg || !profile) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center space-y-4">
        <p className="text-rose-700 font-bold">{errMsg || 'Profile not found'}</p>
        <Link to="/marketplace" className="text-xs text-emerald-700 font-bold hover:underline">← Back to Marketplace</Link>
      </div>
    );
  }

  const { farm, recent_reviews, active_listings } = profile;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <Link to="/marketplace" className="text-xs font-bold text-emerald-700 hover:underline flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> Back to Marketplace
      </Link>

      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="flex items-center gap-5">
          <img
            src={profile.profile_photo_url || "/static/default_avatar.png"}
            alt={profile.name}
            className="w-24 h-24 rounded-full object-cover border-4 border-emerald-500 shadow-md bg-emerald-950"
          />

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-gray-900">{profile.name}</h1>
              {profile.verified && (
                <span className="bg-emerald-100 text-emerald-800 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full flex items-center gap-1 border border-emerald-300">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Verified Member
                </span>
              )}
            </div>

            {farm && <h2 className="text-sm font-extrabold text-emerald-800">{farm.farm_name}</h2>}

            {/* PRIVACY RULE: Eircode & exact address are HIDDEN! Town & County only */}
            <p className="text-xs text-gray-600 flex items-center gap-1">
              <MapPin className="w-4 h-4 text-emerald-600" /> {profile.town}, Co. {profile.county}
            </p>

            <p className="text-[11px] text-gray-500 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Member since {new Date(profile.member_since).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Reputation Badge */}
        <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 text-right space-y-1">
          <span className="text-[10px] font-extrabold text-emerald-800 uppercase tracking-wider block">Reputation Score</span>
          <div className="text-2xl font-black text-emerald-950 flex items-center justify-end gap-1">
            <Award className="w-6 h-6 text-amber-500" /> {profile.reputation_score?.toFixed(1)} / 100
          </div>
          <span className="text-xs text-gray-600 block font-semibold">{profile.total_completed_orders} Orders Completed</span>
        </div>
      </div>

      {/* Farmer Specific Active Listings */}
      {profile.role === 'farmer' && (
        <div className="space-y-4">
          <h3 className="text-lg font-extrabold text-gray-900 flex items-center gap-2 border-b pb-2">
            <ShoppingBag className="w-5 h-5 text-emerald-700" /> Active Farm Surplus Listings ({active_listings.length})
          </h3>

          {active_listings.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {active_listings.map(item => (
                <div key={item.id} className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm space-y-3">
                  <img src={item.image_url} alt={item.product_type} className="w-full h-36 object-cover rounded-xl" />
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-extrabold text-gray-900 capitalize text-sm">{item.product_type}</h4>
                      <p className="text-xs text-gray-500">{item.variety || 'Organic'}</p>
                    </div>
                    <GradeBadge grade={item.quality_grade} score={item.quality_score} />
                  </div>
                  <div className="flex justify-between items-center text-xs border-t pt-2">
                    <span className="font-bold text-emerald-800">€{item.price_per_unit} / {item.quantity_unit}</span>
                    <Link to={`/product/${item.id}`} className="text-emerald-700 font-extrabold hover:underline">View Listing →</Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 bg-gray-50 rounded-2xl text-center text-xs text-gray-500 font-semibold">
              No active surplus listings at the moment.
            </div>
          )}
        </div>
      )}

      {/* Reviews Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-extrabold text-gray-900 flex items-center gap-2 border-b pb-2">
          <Star className="w-5 h-5 text-amber-500" /> Counterparty Reviews
        </h3>

        {recent_reviews.length > 0 ? (
          <div className="space-y-3">
            {recent_reviews.map(rev => (
              <div key={rev.id} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-extrabold text-gray-800 capitalize">{rev.reviewer_role}</span>
                  <div className="flex items-center gap-1 text-amber-500 font-extrabold">
                    ★ {rev.rating} / 5
                  </div>
                </div>
                <p className="text-xs text-gray-600 font-semibold">{rev.review_text}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 bg-gray-50 rounded-2xl text-center text-xs text-gray-500 font-semibold">
            No public reviews submitted yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default PublicProfile;
