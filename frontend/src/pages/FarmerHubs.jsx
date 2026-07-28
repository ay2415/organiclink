import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { MapPin, MessageSquare, Building2, Store, Factory, Utensils } from 'lucide-react';

const FarmerHubs = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [hubs, setHubs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNearestHubs();
  }, []);

  const fetchNearestHubs = async () => {
    const farmId = user?.farm?.id || 'cork-farm-id';
    try {
      const res = await api.get(`/api/hubs/nearest?farm_id=${farmId}&limit=15`);
      setHubs(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getHubIcon = (type) => {
    switch (type) {
      case 'manufacturer': return <Factory className="w-5 h-5 text-purple-600" />;
      case 'store': return <Store className="w-5 h-5 text-emerald-600" />;
      case 'processor': return <Building2 className="w-5 h-5 text-blue-600" />;
      case 'restaurant': return <Utensils className="w-5 h-5 text-amber-600" />;
      default: return <Building2 className="w-5 h-5 text-gray-600" />;
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="border-b pb-4">
        <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
          <MapPin className="w-6 h-6 text-emerald-700" /> Nearest Buyer Directory Hubs
        </h1>
        <p className="text-xs text-gray-500">Seeded Irish organic processors, stores, and restaurants ranked by Haversine distance from your farm</p>
      </div>

      {loading ? (
        <div className="p-8 text-center text-emerald-800 font-bold">Calculating Haversine Distances...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {hubs.map((hub) => (
            <div key={hub.id} className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 bg-gray-50 rounded-lg">{getHubIcon(hub.hub_type)}</div>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase">
                    {hub.distance_km?.toFixed(1)} km away
                  </span>
                </div>

                <h3 className="font-extrabold text-gray-900 text-base">{hub.name}</h3>
                <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600" /> {hub.town}, Co. {hub.county} ({hub.eircode})
                </p>

                <div className="mt-3">
                  <span className="text-[10px] uppercase font-bold text-gray-400 block mb-1">Accepts Produce Types:</span>
                  <div className="flex flex-wrap gap-1">
                    {hub.accepts_products?.map((p, i) => (
                      <span key={i} className="bg-gray-100 text-gray-700 text-[10px] font-bold px-2 py-0.5 rounded-md capitalize">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <button
                onClick={() => navigate(`/messages?hub_id=${hub.id}&hub_name=${encodeURIComponent(hub.name)}`)}
                className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2"
              >
                <MessageSquare className="w-4 h-4" /> Pitch Available Stock to this Buyer
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FarmerHubs;
