import React, { useState, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import CVBreakdownPanel from '../components/CVBreakdownPanel';
import { PlusCircle, Upload, CheckCircle2, AlertTriangle } from 'lucide-react';

const FarmerNewListing = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [productType, setProductType] = useState(searchParams.get('product_type') || 'onion');
  const [variety, setVariety] = useState('Organic Premium');
  const [productionDate, setProductionDate] = useState(new Date().toISOString().split('T')[0]);
  const [availableQuantity, setAvailableQuantity] = useState(parseFloat(searchParams.get('qty')) || 20.0);
  const [quantityUnit, setQuantityUnit] = useState(productType === 'milk' ? 'litre' : 'kg');
  const [pricePerUnit, setPricePerUnit] = useState(2.20);
  const [hoursActive, setHoursActive] = useState(24);
  const [providesTransport, setProvidesTransport] = useState(true);
  const [description, setDescription] = useState('Certified organic surplus available for immediate delivery.');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [cvResult, setCvResult] = useState(null);

  const handleImageChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
      setCvResult(null);
      setError('');
    }
  };

  const handleAnalyzePhoto = async () => {
    if (!imageFile) {
      setError('Please select a produce photo first.');
      return;
    }
    setSubmitting(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('inspection_level', 'farm');
      formData.append('product_type', productType);

      const res = await api.post('/api/quality/analyze', formData);
      setCvResult(res.data.analysis);
    } catch (err) {
      setError('Failed to analyze produce photo.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitListing = async (e) => {
    e.preventDefault();
    if (!imageFile) {
      setError('Please select and upload a produce photo.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const farmId = user?.farm?.id || 'cork-farm-id';
      const formData = new FormData();
      formData.append('product_type', productType);
      formData.append('variety', variety);
      formData.append('production_date', productionDate);
      formData.append('available_quantity', availableQuantity);
      formData.append('quantity_unit', quantityUnit);
      formData.append('price_per_unit', pricePerUnit);
      formData.append('hours_active', hoursActive);
      formData.append('provides_transport', providesTransport);
      formData.append('description', description);
      formData.append('buyer_types_open_to', JSON.stringify(['consumer', 'retailer', 'restaurant', 'institution', 'manufacturer']));
      formData.append('image', imageFile);

      await api.post(`/api/farms/${farmId}/products`, formData);
      navigate('/marketplace');
    } catch (err) {
      setError(err.response?.data?.detail || 'Listing rejected or failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div className="border-b pb-4">
        <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
          <PlusCircle className="w-6 h-6 text-emerald-700" /> List Surplus Produce & Run CV Grading
        </h1>
        <p className="text-xs text-gray-500">Produce is automatically graded by AI Computer Vision before publication (Grades A, B, C accepted; Grade R rejected)</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 p-4 rounded-xl text-xs font-bold flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <div>{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmitListing} className="space-y-6">
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-bold text-gray-900 text-sm border-b pb-2">1. Produce Listing Details</h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="font-bold text-gray-700 block mb-1">Product Type</label>
              <select 
                value={productType} 
                onChange={e=>{
                  setProductType(e.target.value); 
                  setQuantityUnit(e.target.value === 'milk' ? 'litre' : 'kg');
                  setCvResult(null);
                  setError('');
                }} 
                className="w-full border p-2.5 rounded-lg font-semibold"
              >
                <option value="onion">Organic Onion</option>
                <option value="milk">Organic Raw Milk</option>
                <option value="apple">Organic Apple</option>
                <option value="potato">Organic Potato</option>
                <option value="carrot">Organic Carrot</option>
                <option value="cheese">Organic Artisan Cheese</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Variety / Batch Name</label>
              <input type="text" value={variety} onChange={e=>setVariety(e.target.value)} className="w-full border p-2.5 rounded-lg" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Harvest / Harvest Date</label>
              <input type="date" value={productionDate} onChange={e=>setProductionDate(e.target.value)} className="w-full border p-2.5 rounded-lg" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Available Surplus Quantity</label>
              <input type="number" step="0.5" value={availableQuantity} onChange={e=>setAvailableQuantity(parseFloat(e.target.value))} className="w-full border p-2.5 rounded-lg font-bold text-emerald-800" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Quantity Unit</label>
              <select value={quantityUnit} onChange={e=>setQuantityUnit(e.target.value)} className="w-full border p-2.5 rounded-lg">
                <option value="kg">kilograms (kg)</option>
                <option value="litre">litres (L)</option>
                <option value="box">crates / boxes</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Price per Unit (€)</label>
              <input type="number" step="0.05" value={pricePerUnit} onChange={e=>setPricePerUnit(parseFloat(e.target.value))} className="w-full border p-2.5 rounded-lg font-bold" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Hours Active</label>
              <input type="number" step="1" value={hoursActive} onChange={e=>setHoursActive(parseInt(e.target.value))} className="w-full border p-2.5 rounded-lg" />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input type="checkbox" id="transport" checked={providesTransport} onChange={e=>setProvidesTransport(e.target.checked)} className="rounded text-emerald-600 focus:ring-emerald-500" />
            <label htmlFor="transport" className="text-xs font-semibold text-gray-700">Farm offers delivery transport across Ireland</label>
          </div>
        </div>

        {/* Photo Upload & CV Inspection Step */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-bold text-gray-900 text-sm border-b pb-2">2. Computer Vision Quality Photo Upload</h3>

          <div className="flex flex-col sm:flex-row items-center gap-6">
            <div className="w-full sm:w-1/2 border-2 border-dashed border-emerald-200 bg-emerald-50/50 rounded-2xl p-6 text-center">
              {imagePreview ? (
                <img src={imagePreview} alt="Preview" className="max-h-48 mx-auto rounded-lg object-cover shadow" />
              ) : (
                <div className="space-y-2">
                  <Upload className="w-10 h-10 text-emerald-600 mx-auto" />
                  <span className="text-xs font-bold text-gray-700 block">Upload Produce Photo</span>
                  <span className="text-[10px] text-gray-500 block">JPG / PNG format, max 10MB</span>
                </div>
              )}
              <input type="file" accept="image/*" onChange={handleImageChange} className="mt-3 text-xs mx-auto" />
            </div>

            <div className="w-full sm:w-1/2 space-y-3">
              <button
                type="button"
                onClick={handleAnalyzePhoto}
                disabled={!imageFile || submitting}
                className="w-full py-2.5 bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg text-xs font-bold transition-all disabled:opacity-50"
              >
                Run Instant CV Quality Analysis
              </button>

              {cvResult && cvResult.product_mismatch ? (
                <div className="bg-red-50 border border-red-300 text-red-800 p-3 rounded-xl text-xs font-bold mt-2">
                  {cvResult.cv_breakdown?.error || "Product mismatch detected."}
                </div>
              ) : cvResult && (
                <CVBreakdownPanel inspection={{ cv_results: cvResult.cv_breakdown, quality_grade: cvResult.quality_grade, quality_score: cvResult.quality_score }} />
              )}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3.5 bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold rounded-xl shadow-lg transition-all text-sm flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-5 h-5" /> Publish Certified Surplus Listing
        </button>
      </form>
    </div>
  );
};

export default FarmerNewListing;
