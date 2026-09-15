import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Leaf, UserPlus, FileText } from 'lucide-react';
import api from '../api/axios';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    role: 'farmer',
    name: '',
    phone: '',
    cert_body: 'Irish Organic Association',
    cert_number: '',
    expiry_date: ''
  });
  const [certFile, setCertFile] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.role === 'farmer') {
      if (!certFile) {
        setError('Organic Certificate document upload is required for Farmer registration.');
        return;
      }
      if (!formData.cert_number.trim()) {
        setError('Please enter your official Organic Certificate / License Number.');
        return;
      }
      if (!formData.expiry_date) {
        setError('Please enter the certificate expiry date.');
        return;
      }
    }

    setLoading(true);
    try {
      const registerPayload = {
        email: formData.email,
        password: formData.password,
        role: formData.role,
        name: formData.name,
        phone: formData.phone
      };

      const u = await register(registerPayload);

      if (u.role === 'farmer') {
        if (certFile) {
          try {
            const fd = new FormData();
            fd.append('file', certFile);
            fd.append('cert_body', formData.cert_body);
            fd.append('cert_number', formData.cert_number.trim());
            fd.append('expiry_date', formData.expiry_date);
            await api.post('/api/profile/me/certificate', fd);
          } catch (certErr) {
            console.error('Post-registration cert upload error:', certErr);
          }
        }
        navigate('/pending-approval');
      } else {
        navigate('/marketplace');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please verify your details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 bg-white p-8 rounded-2xl shadow-xl border border-emerald-100">
        <div className="text-center">
          <div className="inline-flex p-3 bg-emerald-100 text-emerald-800 rounded-full mb-3">
            <Leaf className="w-8 h-8" />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900">Create Account</h2>
          <p className="mt-2 text-sm text-gray-600">Join Ireland's Certified Organic Marketplace</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs font-semibold">
            {error}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Select Your Platform Role</label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm font-semibold"
            >
              <option value="farmer">Organic Farmer</option>
              <option value="consumer">Individual Consumer</option>
              <option value="retailer">Retailer / Deli / Organic Shop</option>
              <option value="restaurant">Farm-to-Fork Restaurant</option>
              <option value="institution">School / Hospital / Canteen</option>
              <option value="manufacturer">Processor / Aggregator (Contract Buyer)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Full Name / Business Name</label>
            <input
              type="text"
              name="name"
              required
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm"
              placeholder="e.g. Sean O'Mahony"
              value={formData.name}
              onChange={handleChange}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Email Address</label>
            <input
              type="email"
              name="email"
              required
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm"
              placeholder="name@example.com"
              value={formData.email}
              onChange={handleChange}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Phone Number (Irish)</label>
            <input
              type="text"
              name="phone"
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm"
              placeholder="+353 87 123 4567"
              value={formData.phone}
              onChange={handleChange}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Password</label>
            <input
              type="password"
              name="password"
              required
              minLength={8}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm"
              placeholder="•••••••• (Min. 8 characters)"
              value={formData.password}
              onChange={handleChange}
            />
          </div>

          {/* Farmer Certification Gate Fields */}
          {formData.role === 'farmer' && (
            <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200 space-y-3 mt-4">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-800" />
                <span className="font-bold text-xs text-emerald-950 uppercase">Mandatory Organic Certification</span>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 uppercase mb-1">Certification Body</label>
                <select
                  name="cert_body"
                  value={formData.cert_body}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold"
                >
                  <option value="Irish Organic Association">Irish Organic Association (IOA)</option>
                  <option value="Organic Trust">Organic Trust CLG</option>
                  <option value="Global Organic Certification">Other Certified EU Body</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 uppercase mb-1">License / Cert Number *</label>
                <input
                  type="text"
                  name="cert_number"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold"
                  placeholder="e.g. IOA-10842"
                  value={formData.cert_number}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 uppercase mb-1">Certificate Expiry Date *</label>
                <input
                  type="date"
                  name="expiry_date"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold"
                  value={formData.expiry_date}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 uppercase mb-1">Upload Certificate Document (PDF/Image) *</label>
                <input
                  type="file"
                  required
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setCertFile(e.target.files[0])}
                  className="w-full text-xs text-gray-600 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-700 file:text-white hover:file:bg-emerald-800 cursor-pointer"
                />
              </div>
              <p className="text-[10px] text-emerald-800">
                Farmers undergo administrative review before listings become publicly active.
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-md transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50 mt-4"
          >
            <UserPlus className="w-4 h-4" /> {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-xs text-gray-600 pt-4 border-t border-gray-100">
          Already have an account?{' '}
          <Link to="/login" className="font-bold text-emerald-700 hover:underline">
            Sign in here
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
