import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Leaf, UserPlus, FileText } from 'lucide-react';
import api from '../services/api';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    role: 'farmer',
    name: '',
    phone: ''
  });
  const [certFile, setCertFile] = useState(null);
  const [error, setError] = useState('');
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const u = await register(formData);
      if (u.role === 'farmer') {
        if (certFile) {
          try {
            const fd = new FormData();
            fd.append('file', certFile);
            fd.append('cert_body', 'IOA');
            fd.append('cert_number', 'IOA-REG-2026');
            fd.append('expiry_date', '2027-12-31');
            await api.post('/api/profile/me/certificate', fd);
          } catch (certErr) {
            console.error('Post-registration cert upload error:', certErr);
          }
        }
        navigate('/profile');
      } else {
        navigate('/marketplace');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.');
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
              <option value="consumer">Individual Consumer (1-5 kg/L)</option>
              <option value="retailer">Retailer / Deli / Organic Shop</option>
              <option value="restaurant">Farm-to-Fork Restaurant</option>
              <option value="institution">School / Hospital / Canteen</option>
              <option value="manufacturer">Processor / Aggregator (Contract Holder)</option>
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
              placeholder="e.g. sean@glenbegorganic.ie"
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
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
            />
          </div>

          {formData.role === 'farmer' && (
            <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-xl space-y-2">
              <label className="block text-xs font-bold text-amber-900 uppercase flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-amber-700" /> Organic Certificate (PDF or Photo)
              </label>
              <input
                type="file"
                accept="image/*,.pdf"
                onChange={(e) => setCertFile(e.target.files[0])}
                className="w-full text-xs text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-bold file:bg-amber-700 file:text-white hover:file:bg-amber-800 cursor-pointer"
              />
              <p className="text-[11px] text-amber-800 leading-tight">
                Upload your official organic certificate for admin verification.
              </p>
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 px-4 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-md transition-all flex items-center justify-center gap-2 text-sm"
          >
            <UserPlus className="w-4 h-4" /> Create Account
          </button>
        </form>

        <p className="text-center text-xs text-gray-600">
          Already registered?{' '}
          <Link to="/login" className="font-bold text-emerald-700 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
