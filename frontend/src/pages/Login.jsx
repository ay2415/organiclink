import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Leaf, LogIn } from 'lucide-react';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const u = await login(email, password);
      if (u.role === 'farmer') navigate('/farmer/dashboard');
      else if (u.role === 'admin') navigate('/admin');
      else navigate('/marketplace');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check credentials.');
    }
  };

  const handleDemoLogin = async (demoEmail) => {
    try {
      const u = await login(demoEmail, demoEmail.includes('admin') ? 'Admin123!' : 'Password123!');
      if (u.role === 'farmer') navigate('/farmer/dashboard');
      else if (u.role === 'admin') navigate('/admin');
      else navigate('/marketplace');
    } catch (err) {
      setError(err.response?.data?.detail || 'Demo login failed');
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-2xl shadow-xl border border-emerald-100">
        <div className="text-center">
          <div className="inline-flex p-3 bg-emerald-100 text-emerald-800 rounded-full mb-3">
            <Leaf className="w-8 h-8" />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900">Sign in to OrganicLink</h2>
          <p className="mt-2 text-sm text-gray-600">Irish Organic Surplus Marketplace & CV Quality Grading</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-xs font-semibold">
            {error}
          </div>
        )}

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Email Address</label>
            <input
              type="email"
              required
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              placeholder="e.g. farmer@corkorganic.ie"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Password</label>
            <input
              type="password"
              required
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 px-4 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-md transition-all flex items-center justify-center gap-2 text-sm"
          >
            <LogIn className="w-4 h-4" /> Sign In
          </button>
        </form>

        <div className="border-t border-gray-200 pt-6">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider text-center mb-3">Quick Demo Logins</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              onClick={() => handleDemoLogin('farmer@corkorganic.ie')}
              className="p-2 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 font-semibold rounded-md text-left transition-colors border border-emerald-200"
            >
              <div className="font-bold">Cork Onion Farmer</div>
              <div className="text-[10px] text-emerald-600">20kg Surplus Suggestion</div>
            </button>
            <button
              onClick={() => handleDemoLogin('rest1@bistro.ie')}
              className="p-2 bg-blue-50 text-blue-800 hover:bg-blue-100 font-semibold rounded-md text-left transition-colors border border-blue-200"
            >
              <div className="font-bold">Bistro Buyer</div>
              <div className="text-[10px] text-blue-600">Restaurant Role</div>
            </button>
            <button
              onClick={() => handleDemoLogin('admin@organiclink.ie')}
              className="p-2 bg-amber-50 text-amber-900 hover:bg-amber-100 font-semibold rounded-md text-left transition-colors border border-amber-200 col-span-2 text-center"
            >
              <div className="font-bold">System Admin Portal</div>
              <div className="text-[10px] text-amber-700">Dispute Queue & Audit Logs</div>
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-gray-600">
          Don't have an account?{' '}
          <Link to="/register" className="font-bold text-emerald-700 hover:underline">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
