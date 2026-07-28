import React, { useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { User, MapPin, Building, ShieldCheck, Award, FileText, Upload, CheckCircle, Truck, Phone, Mail } from 'lucide-react';

const IRISH_COUNTIES = [
  "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway",
  "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
  "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly",
  "Roscommon", "Sligo", "Tipperary", "Waterford", "Westmeath",
  "Wexford", "Wicklow"
];

const BUYER_TYPES = [
  "Consumer", "Retailer", "Restaurant", "Institution", "Aggregator", "Supermarket", "CSA"
];

const Profile = () => {
  const { user } = useContext(AuthContext);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [errMsg, setErrMsg] = useState('');

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    town: '',
    county: '',
    eircode: '',
    buyer_type: 'Consumer',
    business_name: '',
    vat_number: '',
    delivery_address: '',
    typical_order_size: '',
    // Farmer fields
    farm_name: '',
    size_hectares: '',
    years_farming_organic: '',
    organic_cert_body: 'Irish Organic Association',
    organic_cert_number: '',
    provides_own_transport: true,
  });

  const [certFile, setCertFile] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/profile/me');
      setProfile(res.data);
      const farm = res.data.farm || {};
      setFormData({
        name: res.data.name || '',
        phone: res.data.phone || '',
        town: res.data.town || '',
        county: res.data.county || 'Cork',
        eircode: res.data.eircode || '',
        buyer_type: res.data.buyer_type || 'Consumer',
        business_name: res.data.business_name || '',
        vat_number: res.data.vat_number || '',
        delivery_address: res.data.delivery_address || '',
        typical_order_size: res.data.typical_order_size || '',
        farm_name: farm.farm_name || '',
        size_hectares: farm.size_hectares || '',
        years_farming_organic: farm.years_farming_organic || '',
        organic_cert_body: farm.organic_cert_body || 'Irish Organic Association',
        organic_cert_number: farm.organic_cert_number || '',
        provides_own_transport: farm.provides_own_transport ?? true,
      });
    } catch (err) {
      console.error(err);
      setErrMsg('Failed to load profile details.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg('');
    setErrMsg('');

    try {
      const payload = {
        ...formData,
        size_hectares: formData.size_hectares ? parseFloat(formData.size_hectares) : null,
        years_farming_organic: formData.years_farming_organic ? parseFloat(formData.years_farming_organic) : null,
      };
      await api.patch('/api/profile/me', payload);
      setMsg('Profile updated successfully!');
      fetchProfile();
    } catch (err) {
      setErrMsg(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await api.post('/api/profile/me/photo', fd);
      setProfile(prev => ({ ...prev, profile_photo_url: res.data.profile_photo_url }));
      setMsg('Profile photo uploaded!');
    } catch (err) {
      setErrMsg('Failed to upload profile photo.');
    }
  };

  const handleCertUpload = async (e) => {
    e.preventDefault();
    if (!certFile) return;
    const fd = new FormData();
    fd.append('file', certFile);
    fd.append('cert_body', formData.organic_cert_body);
    fd.append('cert_number', formData.organic_cert_number || 'IOA-REG-2026');
    fd.append('expiry_date', '2027-12-31');

    try {
      await api.post('/api/profile/me/certificate', fd);
      setMsg('Certificate uploaded! Verification is now pending admin review.');
      fetchProfile();
    } catch (err) {
      setErrMsg(err.response?.data?.detail || 'Failed to upload certificate.');
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-emerald-800 font-bold">Loading User Profile...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900 to-emerald-800 text-white rounded-2xl p-6 shadow-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-4">
          <div className="relative">
            <img
              src={profile?.profile_photo_url || "/static/default_avatar.png"}
              alt={profile?.name}
              className="w-20 h-20 rounded-full object-cover border-4 border-emerald-500 shadow-md bg-emerald-950"
            />
            <label className="absolute bottom-0 right-0 bg-emerald-600 hover:bg-emerald-700 text-white p-1.5 rounded-full cursor-pointer shadow-md">
              <Upload className="w-3.5 h-3.5" />
              <input type="file" accept="image/*" onChange={handlePhotoUpload} className="hidden" />
            </label>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold">{profile?.name}</h1>
              <span className="bg-emerald-700 text-emerald-100 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                {profile?.role}
              </span>
            </div>
            <p className="text-xs text-emerald-200 mt-1 flex items-center gap-2">
              <Mail className="w-3.5 h-3.5" /> {profile?.email} | <Phone className="w-3.5 h-3.5" /> {profile?.phone || "No phone added"}
            </p>
            <p className="text-[11px] text-emerald-300 mt-1">
              Member since: {new Date(profile?.created_at).toLocaleDateString()} | Status: <span className="font-bold text-emerald-400 capitalize">{profile?.status}</span>
            </p>
          </div>
        </div>
      </div>

      {msg && <div className="p-4 bg-emerald-100 text-emerald-900 font-bold text-xs rounded-xl border border-emerald-300">{msg}</div>}
      {errMsg && <div className="p-4 bg-rose-100 text-rose-900 font-bold text-xs rounded-xl border border-rose-300">{errMsg}</div>}

      {/* Profile Form */}
      <form onSubmit={handleSave} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-6">
        <h2 className="text-lg font-extrabold text-gray-900 border-b pb-3 flex items-center gap-2">
          <User className="w-5 h-5 text-emerald-700" /> Account & Contact Profile
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Full Name *</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="w-full border p-2.5 rounded-lg text-xs font-semibold"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Phone Number *</label>
            <input
              type="text"
              required
              value={formData.phone}
              onChange={e => setFormData({ ...formData, phone: e.target.value })}
              className="w-full border p-2.5 rounded-lg text-xs font-semibold"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Town / City *</label>
            <input
              type="text"
              required
              value={formData.town}
              onChange={e => setFormData({ ...formData, town: e.target.value })}
              className="w-full border p-2.5 rounded-lg text-xs font-semibold"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">County * (26 Irish Counties)</label>
            <select
              value={formData.county}
              onChange={e => setFormData({ ...formData, county: e.target.value })}
              className="w-full border p-2.5 rounded-lg text-xs font-bold text-emerald-900"
            >
              {IRISH_COUNTIES.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Eircode * (e.g. A65 F4E2)</label>
            <input
              type="text"
              required
              value={formData.eircode}
              onChange={e => setFormData({ ...formData, eircode: e.target.value })}
              className="w-full border p-2.5 rounded-lg text-xs font-mono uppercase"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-gray-700 block mb-1">Account Role (Read-only)</label>
            <input
              type="text"
              disabled
              value={profile?.role?.toUpperCase()}
              className="w-full border p-2.5 rounded-lg text-xs bg-gray-100 font-bold text-gray-500"
            />
          </div>
        </div>

        {/* Farmer Specific Fields */}
        {profile?.role === 'farmer' && (
          <div className="space-y-4 border-t pt-5">
            <h3 className="text-md font-extrabold text-gray-900 flex items-center gap-2">
              <Building className="w-4 h-4 text-emerald-700" /> Farm Profile Details
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Farm Name *</label>
                <input
                  type="text"
                  required
                  value={formData.farm_name}
                  onChange={e => setFormData({ ...formData, farm_name: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Farm Size (Hectares)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.size_hectares}
                  onChange={e => setFormData({ ...formData, size_hectares: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Years Farming Organic</label>
                <input
                  type="number"
                  value={formData.years_farming_organic}
                  onChange={e => setFormData({ ...formData, years_farming_organic: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Organic Certification Body</label>
                <select
                  value={formData.organic_cert_body}
                  onChange={e => setFormData({ ...formData, organic_cert_body: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                >
                  <option value="Irish Organic Association">Irish Organic Association (IOA)</option>
                  <option value="Organic Trust">Organic Trust</option>
                  <option value="Demeter">Demeter</option>
                  <option value="Other">Other Certified Body</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Certification Number</label>
                <input
                  type="text"
                  value={formData.organic_cert_number}
                  onChange={e => setFormData({ ...formData, organic_cert_number: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="provides_transport"
                  checked={formData.provides_own_transport}
                  onChange={e => setFormData({ ...formData, provides_own_transport: e.target.checked })}
                  className="w-4 h-4 text-emerald-600 rounded"
                />
                <label htmlFor="provides_transport" className="text-xs font-bold text-gray-800">
                  Farm Provides Own Delivery Transport
                </label>
              </div>
            </div>

            {/* Organic Certificate Upload Box */}
            <div className="p-4 bg-emerald-50/50 rounded-xl border border-emerald-200 space-y-3">
              <h4 className="text-xs font-extrabold text-emerald-950 flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-emerald-700" /> Organic Certificate Document
              </h4>
              <p className="text-[11px] text-gray-600">
                Upload your official organic certificate PDF or image for admin verification.
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="file"
                  onChange={e => setCertFile(e.target.files[0])}
                  className="text-xs"
                />
                <button
                  type="button"
                  onClick={handleCertUpload}
                  disabled={!certFile}
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs rounded-lg shadow-sm disabled:opacity-50"
                >
                  Upload Cert Document
                </button>
              </div>
              {profile?.farm?.cert_doc_url && (
                <div className="text-xs text-emerald-800 font-bold flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" /> Certificate uploaded (Status: {profile?.farm?.verification_status})
                </div>
              )}
            </div>
          </div>
        )}

        {/* Buyer Specific Fields */}
        {profile?.role !== 'farmer' && profile?.role !== 'admin' && (
          <div className="space-y-4 border-t pt-5">
            <h3 className="text-md font-extrabold text-gray-900 flex items-center gap-2">
              <Building className="w-4 h-4 text-emerald-700" /> Buyer Business Details
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Buyer Category</label>
                <select
                  value={formData.buyer_type}
                  onChange={e => setFormData({ ...formData, buyer_type: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-bold text-emerald-900"
                >
                  {BUYER_TYPES.map(b => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Business Name</label>
                <input
                  type="text"
                  value={formData.business_name}
                  onChange={e => setFormData({ ...formData, business_name: e.target.value })}
                  placeholder="Required for commercial buyers"
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">VAT Number (Optional)</label>
                <input
                  type="text"
                  value={formData.vat_number}
                  onChange={e => setFormData({ ...formData, vat_number: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">Typical Order Quantity (e.g. 50kg/week)</label>
                <input
                  type="text"
                  value={formData.typical_order_size}
                  onChange={e => setFormData({ ...formData, typical_order_size: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs font-bold text-gray-700 block mb-1">Default Delivery Address</label>
                <textarea
                  rows="2"
                  value={formData.delivery_address}
                  onChange={e => setFormData({ ...formData, delivery_address: e.target.value })}
                  className="w-full border p-2.5 rounded-lg text-xs font-semibold"
                />
              </div>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full py-3.5 bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold rounded-xl shadow-md transition-all text-sm"
        >
          {saving ? 'Saving Profile...' : 'Save Profile Changes'}
        </button>
      </form>
    </div>
  );
};

export default Profile;
