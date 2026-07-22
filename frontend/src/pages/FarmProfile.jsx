import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';
import GradeBadge from '../components/GradeBadge';
import { ShieldCheck, MapPin, Award, Store } from 'lucide-react';

const FarmProfile = () => {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFarm();
  }, [id]);

  const fetchFarm = async () => {
    try {
      const res = await api.get(`/api/farms/${id}`);
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return <div className="p-12 text-center text-emerald-800 font-bold">Loading Farm Profile...</div>;
  }

  const { farm, active_listings, ratings_reviews } = data;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <div className="bg-emerald-950 text-white p-8 rounded-3xl shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <span className="bg-emerald-700 text-emerald-200 text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 mb-3">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> {farm.organic_cert_body} ({farm.organic_cert_number})
          </span>
          <h1 className="text-3xl font-extrabold">{farm.farm_name}</h1>
          <p className="text-xs text-emerald-300 flex items-center gap-1.5 mt-1">
            <MapPin className="w-4 h-4 text-emerald-400" /> {farm.town}, Co. {farm.county} | Eircode: {farm.eircode}
          </p>
        </div>

        <div className="bg-emerald-900/60 border border-emerald-700 p-4 rounded-2xl text-center">
          <span className="text-xs uppercase font-bold text-emerald-300 block">Reputation Score</span>
          <span className="text-2xl font-extrabold text-amber-400 flex items-center gap-1 justify-center">
            <Award className="w-6 h-6 text-amber-400" /> {farm.reputation_score.toFixed(1)} / 100
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-extrabold text-gray-900 flex items-center gap-2">
          <Store className="w-5 h-5 text-emerald-700" /> Active Surplus Listings
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {active_listings.map((prod) => (
            <Link key={prod.id} to={`/product/${prod.id}`} className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all">
              <img src={prod.image_url} alt={prod.product_type} className="w-full h-40 object-cover rounded-xl mb-3" />
              <div className="flex justify-between items-center">
                <span className="font-bold text-gray-900 capitalize">Organic {prod.product_type}</span>
                <GradeBadge grade={prod.quality_grade} score={prod.quality_score} />
              </div>
              <div className="text-xs text-emerald-800 font-extrabold mt-2">
                €{prod.price_per_unit.toFixed(2)} / {prod.quantity_unit} ({prod.available_quantity} available)
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FarmProfile;
