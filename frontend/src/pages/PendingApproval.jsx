import React, { useContext, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { ShieldAlert, Clock, RefreshCw, LogOut, FileText, XCircle } from 'lucide-react';
import api from '../api/axios';

const PendingApproval = () => {
  const { user, logout } = useContext(AuthContext);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState('');

  const isRejected = user?.status === 'rejected' || user?.farm?.verification_status === 'rejected';

  const handleCheckStatus = async () => {
    setChecking(true);
    setMessage('');
    try {
      const res = await api.get('/api/auth/me');
      if (res.data.status === 'verified' || res.data.verified) {
        window.location.href = '/farmer/dashboard';
      } else {
        setMessage('Status update: Your account is still pending admin review.');
      }
    } catch (err) {
      setMessage('Unable to check status at this moment.');
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-3xl p-8 shadow-xl border border-gray-200 text-center space-y-6">
        <div className={`inline-flex p-4 rounded-full ${isRejected ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-800'}`}>
          {isRejected ? <XCircle className="w-10 h-10" /> : <Clock className="w-10 h-10 animate-pulse" />}
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold text-gray-900">
            {isRejected ? 'Account Verification Rejected' : 'Waiting for Admin Approval'}
          </h1>
          <p className="text-xs text-gray-600 leading-relaxed">
            {isRejected
              ? 'Your organic certificate verification was reviewed and rejected by an administrator. Platform seller features and marketplace access remain locked.'
              : 'Thank you for registering your farm! Your uploaded organic certificate is currently under review by an administrator. Platform seller access, profile, and marketplace listing features are restricted until verified.'}
          </p>
        </div>

        {message && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs font-bold text-amber-900">
            {message}
          </div>
        )}

        <div className="bg-gray-50 p-4 rounded-2xl border border-gray-200 text-left text-xs space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-500">Account Role:</span>
            <span className="font-bold text-gray-900 capitalize">{user?.role}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Registered Email:</span>
            <span className="font-bold text-gray-900">{user?.email}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">Verification Status:</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${isRejected ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}`}>
              {user?.status || 'pending'}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3 pt-2">
          {!isRejected && (
            <button
              onClick={handleCheckStatus}
              disabled={checking}
              className="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow"
            >
              <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} /> Refresh Approval Status
            </button>
          )}

          <button
            onClick={logout}
            className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl text-xs flex items-center justify-center gap-2"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </div>
    </div>
  );
};

export default PendingApproval;
