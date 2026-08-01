import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import GradeBadge from '../components/GradeBadge';
import { Search, Filter, MapPin, Truck, Award, ShieldCheck, Flame } from 'lucide-react';

const Marketplace = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [productType, setProductType] = useState('');
  const [county, setCounty] = useState('');
  const [minGrade, setMinGrade] = useState('');
  const [maxDistance, setMaxDistance] = useState('');
  const [sort, setSort] = useState('newest');

  useEffect(() => {
    fetchMarketplace();
  }, [productType, county, minGrade, maxDistance, sort]);

  const fetchMarketplace = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (productType) params.append('product_type', productType);
      if (county) params.append('county', county);
      if (minGrade) params.append('min_grade', minGrade);
      if (maxDistance) params.append('max_distance_km', maxDistance);
      if (sort) params.append('sort', sort);

      const res = await api.get(`/api/marketplace?${params.toString()}`);
      setProducts(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Banner */}
      <div className="bg-gradient-to-r from-emerald-900 to-emerald-800 text-white rounded-2xl p-6 shadow-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="bg-emerald-700 text-emerald-200 text-[10px] font-extrabold px-3 py-1 rounded-full uppercase tracking-wider mb-2 inline-block">
            100% Certified Irish Organic Available Stock
          </span>
          <h1 className="text-2xl font-extrabold">Irish Organic Farm Available Stock Marketplace</h1>
          <p className="text-xs text-emerald-200 mt-1">Computer vision AI quality graded produce & milk directly from certified Irish farms</p>
        </div>

        <div className="flex items-center gap-3">
          <select value={sort} onChange={e=>setSort(e.target.value)} className="bg-emerald-950 text-white border border-emerald-700 text-xs font-bold rounded-lg px-3 py-2">
            <option value="newest">Sort by: Newest Listed</option>
            <option value="distance">Sort by: Nearest Distance</option>
            <option value="price">Sort by: Lowest Price</option>
            <option value="grade">Sort by: Highest Quality Grade</option>
          </select>
        </div>
      </div>

      {/* Main Grid + Sidebar Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar Filters */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm space-y-5 h-fit">
          <div className="flex items-center justify-between border-b pb-3 font-bold text-gray-900 text-sm">
            <span className="flex items-center gap-1.5"><Filter className="w-4 h-4 text-emerald-700" /> Filter Stock</span>
            <button onClick={()=>{setProductType(''); setCounty(''); setMinGrade(''); setMaxDistance('');}} className="text-[10px] text-emerald-700 hover:underline">Reset</button>
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Produce / Dairy Type</label>
            <select value={productType} onChange={e=>setProductType(e.target.value)} className="w-full border p-2 rounded-lg text-xs font-semibold">
              <option value="">All Produce Types</option>
              <option value="apple">Organic Apple</option>
              <option value="banana">Organic Banana</option>
              <option value="bitter_gourd">Organic Bitter Gourd</option>
              <option value="capsicum">Organic Capsicum</option>
              <option value="milk">Organic Raw Milk</option>
              <option value="orange">Organic Orange</option>
              <option value="tomato">Organic Tomato</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Irish County</label>
            <select value={county} onChange={e=>setCounty(e.target.value)} className="w-full border p-2 rounded-lg text-xs font-semibold">
              <option value="">All 26 Counties</option>
              <option value="Cork">Co. Cork</option>
              <option value="Galway">Co. Galway</option>
              <option value="Tipperary">Co. Tipperary</option>
              <option value="Kildare">Co. Kildare</option>
              <option value="Cavan">Co. Cavan</option>
              <option value="Limerick">Co. Limerick</option>
              <option value="Waterford">Co. Waterford</option>
              <option value="Clare">Co. Clare</option>
              <option value="Dublin">Co. Dublin</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Minimum Quality Grade</label>
            <select value={minGrade} onChange={e=>setMinGrade(e.target.value)} className="w-full border p-2 rounded-lg text-xs font-semibold">
              <option value="">All Grades (A, B, C)</option>
              <option value="A">Grade A (Premium ≥85)</option>
              <option value="B">Grade B (Good ≥70)</option>
              <option value="C">Grade C (Fair ≥50)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Max Distance (km)</label>
            <select value={maxDistance} onChange={e=>setMaxDistance(e.target.value)} className="w-full border p-2 rounded-lg text-xs font-semibold">
              <option value="">Any Distance</option>
              <option value="50">Within 50 km</option>
              <option value="100">Within 100 km</option>
              <option value="200">Within 200 km</option>
            </select>
          </div>
        </div>

        {/* Product Cards Feed */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="p-12 text-center text-emerald-800 font-bold">Loading Marketplace Feed...</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {products.map((prod) => (
                <Link
                  key={prod.id}
                  to={`/product/${prod.id}`}
                  className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between group"
                >
                  <div>
                    {/* Image Header with Grade Badge Overlay */}
                    <div className="relative h-48 bg-gray-100 overflow-hidden">
                      <img src={prod.image_url} alt={prod.product_type} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                      <div className="absolute top-3 right-3 shadow-md">
                        <GradeBadge grade={prod.quality_grade} score={prod.quality_score} />
                      </div>
                      <div className="absolute bottom-3 left-3 bg-emerald-950/80 backdrop-blur-sm text-white text-[10px] font-extrabold px-2.5 py-1 rounded-full flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> {prod.is_bulk ? `Bulk Batch (${prod.bulk_summary || 'Multi-Item'})` : '100% Certified Organic'}
                      </div>
                    </div>

                    {/* Card Content */}
                    <div className="p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="font-extrabold text-gray-900 text-base capitalize group-hover:text-emerald-700 transition-colors">
                          Organic {prod.product_type}
                        </h3>
                        <span className="text-xs font-bold text-gray-500">{prod.available_quantity} {prod.quantity_unit}</span>
                      </div>

                      <div className="text-xs text-gray-500 flex items-center justify-between">
                        <span className="flex items-center gap-1 font-semibold text-gray-700">
                          <MapPin className="w-3.5 h-3.5 text-emerald-600" /> {prod.town}, Co. {prod.county}
                        </span>
                        <span className="font-bold text-emerald-800">{prod.distance_km?.toFixed(1)} km</span>
                      </div>

                      <div className="text-xs text-gray-600 flex items-center justify-between pt-1">
                        <span className="text-gray-500">{prod.farm_name}</span>
                        <span className="text-amber-600 font-bold flex items-center gap-0.5">
                          <Award className="w-3.5 h-3.5" /> {prod.farmer_reputation?.toFixed(1)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Footer Price Banner */}
                  <div className="p-4 bg-emerald-50/50 border-t border-emerald-100 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase font-bold block">Surplus Price</span>
                      <span className="text-lg font-extrabold text-emerald-800">€{prod.price_per_unit.toFixed(2)} <span className="text-xs text-gray-500 font-normal">/ {prod.quantity_unit}</span></span>
                    </div>

                    {prod.provides_transport && (
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full flex items-center gap-1">
                        <Truck className="w-3 h-3" /> Delivery Available
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Marketplace;
