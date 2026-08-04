import React, { useState, useContext, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import CVBreakdownPanel from '../components/CVBreakdownPanel';
import CameraOrUploadInput from '../components/CameraOrUploadInput';
import { PlusCircle, Upload, CheckCircle2, AlertTriangle, Camera, X } from 'lucide-react';

const FarmerNewListing = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [productType, setProductType] = useState(searchParams.get('product_type') || 'tomato');
  const [variety, setVariety] = useState('Organic Premium');
  const [productionDate, setProductionDate] = useState(new Date().toISOString().split('T')[0]);
  const [availableQuantity, setAvailableQuantity] = useState(parseFloat(searchParams.get('qty')) || 20.0);
  const [quantityUnit, setQuantityUnit] = useState(productType === 'milk' ? 'litre' : 'kg');
  const [pricePerUnit, setPricePerUnit] = useState(2.20);
  const [hoursActive, setHoursActive] = useState(24);
  const [providesTransport, setProvidesTransport] = useState(true);
  const [isBulk, setIsBulk] = useState(true);
  const [description, setDescription] = useState('Certified organic surplus available for immediate delivery.');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [cvResult, setCvResult] = useState(null);

  const [showCameraModal, setShowCameraModal] = useState(false);
  const videoRef = useRef(null);
  const cameraInputRef = useRef(null);
  const [mediaStream, setMediaStream] = useState(null);

  const startCamera = async () => {
    try {
      setShowCameraModal(true);
      setError('');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      setMediaStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Camera access error:", err);
      setError("Unable to access camera. Please allow camera permissions or use file upload.");
      setShowCameraModal(false);
    }
  };

  const stopCamera = () => {
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      setMediaStream(null);
    }
    setShowCameraModal(false);
  };

  const capturePhotoFromCamera = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `camera_snap_${Date.now()}.jpg`, { type: 'image/jpeg' });
        setImageFile(file);
        setImagePreview(URL.createObjectURL(file));
        setCvResult(null);
        setError('');
      }
      stopCamera();
    }, 'image/jpeg', 0.92);
  };

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
      formData.append('is_bulk', isBulk);

      const res = await api.post('/api/quality/analyze', formData);
      if (res.data.analysis?.product_mismatch) {
        setError(res.data.analysis.message || 'Product mismatch detected.');
        setCvResult(null);
        return;
      }
      setCvResult(res.data.analysis);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze produce photo.');
      setCvResult(null);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitListing = async (e) => {
    e.preventDefault();
    if (!imageFile && productType !== 'milk') {
      setError('Please select and upload a produce photo for visual quality grading.');
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
      formData.append('is_bulk', isBulk);
      formData.append('description', description);
      formData.append('buyer_types_open_to', JSON.stringify(['consumer', 'retailer', 'restaurant', 'institution', 'manufacturer']));
      if (imageFile) {
        formData.append('image', imageFile);
      }

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
          <PlusCircle className="w-6 h-6 text-emerald-700" /> List Available Produce & Run CV Grading
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
                onChange={e => {
                  setProductType(e.target.value);
                  setQuantityUnit(e.target.value === 'milk' ? 'litre' : 'kg');
                  setCvResult(null);
                  setError('');
                }}
                className="w-full border p-2.5 rounded-lg font-semibold"
              >
                <optgroup label="🌟 Verified High-Accuracy Produce Crops">
                  <option value="tomato">Organic Tomato</option>
                  <option value="apple">Organic Apple</option>
                  <option value="banana">Organic Banana</option>
                  <option value="mango">Organic Mango</option>
                  <option value="orange">Organic Orange</option>
                  <option value="capsicum">Organic Capsicum / Bell Pepper</option>
                  <option value="guava">Organic Guava</option>
                  <option value="potato">Organic Potato</option>
                </optgroup>

                <optgroup label="🥛 Non-CV & Milk Declarations">
                  <option value="milk">Organic Raw Milk (Declaration Only)</option>
                  <option value="onion">Organic Onion (Non-CV)</option>
                  <option value="spinach">Organic Spinach / Leafy Greens (Non-CV)</option>
                </optgroup>
              </select>
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Variety / Batch Name</label>
              <input type="text" value={variety} onChange={e => setVariety(e.target.value)} className="w-full border p-2.5 rounded-lg" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Harvest / Harvest Date</label>
              <input type="date" value={productionDate} onChange={e => setProductionDate(e.target.value)} className="w-full border p-2.5 rounded-lg" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Available Quantity</label>
              <input type="number" step="0.5" value={availableQuantity} onChange={e => setAvailableQuantity(parseFloat(e.target.value))} className="w-full border p-2.5 rounded-lg font-bold text-emerald-800" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Quantity Unit</label>
              <select value={quantityUnit} onChange={e => setQuantityUnit(e.target.value)} className="w-full border p-2.5 rounded-lg">
                <option value="kg">kilograms (kg)</option>
                <option value="litre">litres (L)</option>
                <option value="box">crates / boxes</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Price per Unit (€)</label>
              <input type="number" step="0.05" value={pricePerUnit} onChange={e => setPricePerUnit(parseFloat(e.target.value))} className="w-full border p-2.5 rounded-lg font-bold" />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Hours Active</label>
              <input type="number" step="1" value={hoursActive} onChange={e => setHoursActive(parseInt(e.target.value))} className="w-full border p-2.5 rounded-lg" />
            </div>

            <div className="sm:col-span-3 bg-emerald-50/70 p-3.5 rounded-xl border border-emerald-200 flex items-center justify-between mt-2">
              <div>
                <span className="font-bold text-emerald-950 text-xs block">Bulk / Multiple Items Mode (YOLOv8 Two-Stage Pipeline)</span>
                <span className="text-[11px] text-emerald-700 block">Check this if your photo contains a batch/tray of multiple items. Items are localized with YOLO and graded individually.</span>
              </div>
              <input
                type="checkbox"
                checked={isBulk}
                onChange={e => setIsBulk(e.target.checked)}
                className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input type="checkbox" id="transport" checked={providesTransport} onChange={e => setProvidesTransport(e.target.checked)} className="rounded text-emerald-600 focus:ring-emerald-500" />
            <label htmlFor="transport" className="text-xs font-semibold text-gray-700">Farm offers delivery transport across Ireland</label>
          </div>
        </div>

        {/* Photo Upload & CV Inspection Step */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-bold text-gray-900 text-sm border-b pb-2">2. Computer Vision Quality Photo Upload</h3>

          <div className="flex flex-col sm:flex-row items-center gap-6">
            <div className="w-full sm:w-1/2 border-2 border-dashed border-emerald-200 bg-emerald-50/50 rounded-2xl p-5 text-center">
              <CameraOrUploadInput
                currentPreview={imagePreview}
                onFileSelected={(file) => {
                  setImageFile(file);
                  setImagePreview(URL.createObjectURL(file));
                  setCvResult(null);
                  setError('');
                }}
              />
            </div>

            <div className="w-full sm:w-1/2 space-y-3">
              {productType === 'milk' ? (
                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center space-y-1">
                  <span className="text-xs font-bold text-slate-700 block">Visual grading not applicable</span>
                  <span className="text-[11px] text-slate-500 block">Milk & liquid dairy quality indicators (fat, protein, bacteria) are lab-certified. Photo is recorded without CV grade.</span>
                </div>
              ) : (
                <>
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
                </>
              )}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3.5 bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold rounded-xl shadow-lg transition-all text-sm flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-5 h-5" /> Publish Certified Available Listing
        </button>
      </form>


    </div>
  );
};

export default FarmerNewListing;
