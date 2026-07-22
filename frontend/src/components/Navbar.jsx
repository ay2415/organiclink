import React, { useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Leaf, Store, ShoppingBag, Shield, LogOut, MessageSquare, MapPin } from 'lucide-react';

const Navbar = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-emerald-950 text-white shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center space-x-2.5">
            <div className="bg-emerald-500 p-2 rounded-lg text-emerald-950 font-bold">
              <Leaf className="w-5 h-5 fill-current" />
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-white">Organic<span className="text-emerald-400">Link</span></span>
              <span className="text-[10px] block text-emerald-300 tracking-wider -mt-1 font-semibold">IRISH ORGANIC SURPLUS MARKETPLACE</span>
            </div>
          </Link>

          <div className="hidden md:flex items-center space-x-6 text-sm font-medium">
            <Link to="/marketplace" className="hover:text-emerald-400 transition-colors flex items-center gap-1.5">
              <Store className="w-4 h-4" /> Marketplace
            </Link>

            {user?.role === 'farmer' && (
              <>
                <Link to="/farmer/dashboard" className="hover:text-emerald-400 transition-colors">Dashboard</Link>
                <Link to="/farmer/production" className="hover:text-emerald-400 transition-colors">Yields</Link>
                <Link to="/farmer/contracts" className="hover:text-emerald-400 transition-colors">Contracts</Link>
                <Link to="/farmer/hubs" className="hover:text-emerald-400 transition-colors flex items-center gap-1">
                  <MapPin className="w-4 h-4 text-emerald-400" /> Nearest Buyers
                </Link>
                <Link to="/farmer/listings/new" className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all">
                  + List Surplus
                </Link>
              </>
            )}

            {user && user.role !== 'farmer' && user.role !== 'admin' && (
              <Link to="/buyer/dashboard" className="hover:text-emerald-400 transition-colors flex items-center gap-1">
                <ShoppingBag className="w-4 h-4" /> My Orders & Invoices
              </Link>
            )}

            {user?.role === 'admin' && (
              <Link to="/admin" className="bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1">
                <Shield className="w-4 h-4" /> Admin Portal
              </Link>
            )}

            {user && (
              <Link to="/messages" className="hover:text-emerald-400 transition-colors flex items-center gap-1">
                <MessageSquare className="w-4 h-4" /> Messages
              </Link>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {user ? (
              <div className="flex items-center space-x-3">
                <div className="text-right hidden sm:block">
                  <div className="text-xs font-semibold text-white">{user.name}</div>
                  <div className="text-[10px] text-emerald-400 uppercase font-bold tracking-wide">{user.role}</div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-emerald-300 hover:text-white hover:bg-emerald-900 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-xs font-bold">
                <Link to="/login" className="px-3 py-2 text-emerald-200 hover:text-white">Login</Link>
                <Link to="/register" className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg shadow-sm">Register</Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
