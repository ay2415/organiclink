import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import GradeBadge from '../components/GradeBadge';
import {
  Shield, AlertTriangle, CheckCircle2, FileText, Settings, Activity, Gavel
} from 'lucide-react';

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('disputes');

  const [metrics, setMetrics] = useState(null);
  const [disputes, setDisputes] = useState([]);
  const [farmsQueue, setFarmsQueue] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [adminSettings, setAdminSettings] = useState({
    variance_tolerance_percent: 10.0,
    min_listing_grade: 'C',
    commission_percent: 5.0,
    payment_terms_days: 14
  });

  const [resolutionState, setResolutionState] = useState({});

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const metRes = await api.get('/api/admin/metrics');
      setMetrics(metRes.data);

      const dispRes = await api.get('/api/admin/disputes?status=open');
      setDisputes(dispRes.data || []);

      const farmRes = await api.get('/api/admin/farms?verified=false');
      setFarmsQueue(farmRes.data || []);

      const auditRes = await api.get('/api/admin/audit-logs?limit=50');
      setAuditLogs(auditRes.data || []);

      const setRes = await api.get('/api/admin/settings');
      setAdminSettings(setRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleVerifyFarm = async (farmId, verified) => {
    try {
      await api.put(`/api/admin/farms/${farmId}/verify`, { verified, note: 'Admin verified certification' });
      fetchAdminData();
    } catch (err) {
      alert('Error verifying farm');
    }
  };

  const handleResolveDispute = async (orderId) => {
    const resState = resolutionState[orderId] || { resolution: 'partial_payment', rationale: 'Resolved by admin evaluation', partial_percent: 50.0 };
    try {
      await api.put(`/api/admin/disputes/${orderId}/resolve`, resState);
      fetchAdminData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error resolving dispute');
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    try {
      await api.put('/api/admin/settings', adminSettings);
      alert('Admin settings saved successfully');
      fetchAdminData();
    } catch (err) {
      alert('Error saving admin settings');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-amber-900 to-amber-950 text-white rounded-3xl p-6 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-6 h-6 text-amber-400" />
            <h1 className="text-2xl font-extrabold">OrganicLink Admin & Dispute Resolution Portal</h1>
          </div>
          <p className="text-xs text-amber-200">System governance, quality variance dispute arbitration, farm verification queue, and immutable audit logs</p>
        </div>
      </div>

      {/* Metrics Row */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm text-center">
            <span className="text-[10px] text-gray-500 uppercase font-bold block">Total Users</span>
            <span className="text-2xl font-extrabold text-gray-900">{metrics.total_users}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm text-center">
            <span className="text-[10px] text-gray-500 uppercase font-bold block">Verified Farms</span>
            <span className="text-2xl font-extrabold text-emerald-700">{metrics.verified_farms} / {metrics.total_farms}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm text-center">
            <span className="text-[10px] text-gray-500 uppercase font-bold block">Completed Sales</span>
            <span className="text-2xl font-extrabold text-blue-700">{metrics.completed_orders}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm text-center">
            <span className="text-[10px] text-gray-500 uppercase font-bold block">Open Disputes</span>
            <span className="text-2xl font-extrabold text-red-700">{disputes.length}</span>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm text-center col-span-2 sm:col-span-1">
            <span className="text-[10px] text-gray-500 uppercase font-bold block">Gross Volume</span>
            <span className="text-2xl font-extrabold text-emerald-800">€{metrics.gross_trade_volume_eur?.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 text-xs font-bold space-x-6">
        <button
          onClick={() => setActiveTab('disputes')}
          className={`pb-3 border-b-2 flex items-center gap-1.5 ${activeTab === 'disputes' ? 'border-amber-600 text-amber-700' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
        >
          <Gavel className="w-4 h-4" /> Dispute Arbitration Queue ({disputes.length})
        </button>
        <button
          onClick={() => setActiveTab('farms')}
          className={`pb-3 border-b-2 flex items-center gap-1.5 ${activeTab === 'farms' ? 'border-amber-600 text-amber-700' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
        >
          <CheckCircle2 className="w-4 h-4" /> Unverified Farms ({farmsQueue.length})
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`pb-3 border-b-2 flex items-center gap-1.5 ${activeTab === 'audit' ? 'border-amber-600 text-amber-700' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
        >
          <Activity className="w-4 h-4" /> Immutable Audit Log
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`pb-3 border-b-2 flex items-center gap-1.5 ${activeTab === 'settings' ? 'border-amber-600 text-amber-700' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
        >
          <Settings className="w-4 h-4" /> Platform Settings
        </button>
      </div>

      {/* TAB 1: DISPUTE RESOLUTION QUEUE */}
      {activeTab === 'disputes' && (
        <div className="space-y-6">
          {disputes.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-2xl border text-gray-500 text-xs">
              No open quality disputes in queue. All quality variances are within tolerance!
            </div>
          ) : (
            disputes.map((d) => (
              <div key={d.order_id} className="bg-white rounded-3xl border border-red-200 p-6 shadow-md space-y-6">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-base text-gray-900">Order #{d.order_id.substring(0, 8)}</span>
                      <span className="bg-red-100 text-red-800 text-xs font-bold px-3 py-0.5 rounded-full uppercase">
                        {d.quality_variance_percent?.toFixed(1)}% Variance Flagged
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      Farmer: <span className="font-bold text-gray-800">{d.farmer?.name}</span> | Buyer: <span className="font-bold text-gray-800">{d.buyer?.name}</span> ({d.buyer?.role}) | Total: <span className="font-extrabold text-emerald-800">€{d.total_price.toFixed(2)}</span>
                    </p>
                  </div>
                  <div className="bg-red-50 text-red-900 text-xs font-bold px-3 py-2 rounded-xl border border-red-200">
                    Payment Held in Escrow
                  </div>
                </div>

                <div className="bg-red-50/50 p-4 rounded-2xl border border-red-100 text-xs text-red-900">
                  <span className="font-bold">Automated Flag Reason: </span>{d.dispute_reason}
                </div>

                {/* Side by Side Image & Score Inspection Comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gray-50 p-4 rounded-2xl border border-gray-200 space-y-2">
                    <div className="flex justify-between items-center text-xs font-bold text-gray-800">
                      <span>Farm Dispatch Photo</span>
                      <GradeBadge grade={d.farm_inspection?.grade} score={d.farm_inspection?.score} />
                    </div>
                    {d.farm_inspection?.image_url && (
                      <img src={d.farm_inspection.image_url} alt="Farm" className="w-full h-40 object-cover rounded-xl" />
                    )}
                  </div>

                  <div className="bg-gray-50 p-4 rounded-2xl border border-gray-200 space-y-2">
                    <div className="flex justify-between items-center text-xs font-bold text-gray-800">
                      <span>Delivery Arrival Photo</span>
                      <GradeBadge grade={d.delivery_inspection?.grade} score={d.delivery_inspection?.score} />
                    </div>
                    {d.delivery_inspection?.image_url && (
                      <img src={d.delivery_inspection.image_url} alt="Delivery" className="w-full h-40 object-cover rounded-xl" />
                    )}
                  </div>
                </div>

                {/* Admin Resolution Controls */}
                <div className="bg-amber-50/60 p-5 rounded-2xl border border-amber-200 space-y-4">
                  <h4 className="font-extrabold text-amber-950 text-xs uppercase tracking-wider">Arbitration Verdict Controls</h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                    <div>
                      <label className="font-bold text-gray-700 block mb-1">Resolution Decision</label>
                      <select
                        value={resolutionState[d.order_id]?.resolution || 'partial_payment'}
                        onChange={e=>setResolutionState({ ...resolutionState, [d.order_id]: { ...resolutionState[d.order_id], resolution: e.target.value } })}
                        className="w-full border p-2 rounded-lg font-bold"
                      >
                        <option value="partial_payment">Partial Payment (Split Risk)</option>
                        <option value="full_payment">Full Payment to Farmer (Quality Maintained)</option>
                        <option value="refund_buyer">Full Refund to Buyer (Quality Defective)</option>
                      </select>
                    </div>

                    {resolutionState[d.order_id]?.resolution === 'partial_payment' && (
                      <div>
                        <label className="font-bold text-gray-700 block mb-1">Farmer Payment %</label>
                        <input
                          type="number"
                          value={resolutionState[d.order_id]?.partial_percent ?? 50.0}
                          onChange={e=>setResolutionState({ ...resolutionState, [d.order_id]: { ...resolutionState[d.order_id], partial_percent: parseFloat(e.target.value) } })}
                          className="w-full border p-2 rounded-lg font-bold text-amber-900"
                        />
                      </div>
                    )}

                    <div className="sm:col-span-2">
                      <label className="font-bold text-gray-700 block mb-1">Arbitration Rationale Note</label>
                      <input
                        type="text"
                        value={resolutionState[d.order_id]?.rationale || ''}
                        onChange={e=>setResolutionState({ ...resolutionState, [d.order_id]: { ...resolutionState[d.order_id], rationale: e.target.value } })}
                        placeholder="State reason for resolution decision..."
                        className="w-full border p-2 rounded-lg text-xs"
                      />
                    </div>
                  </div>

                  <button
                    onClick={() => handleResolveDispute(d.order_id)}
                    className="px-6 py-2.5 bg-amber-700 hover:bg-amber-800 text-white font-extrabold text-xs rounded-xl shadow transition-all"
                  >
                    Execute Binding Dispute Resolution
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* TAB 2: FARM VERIFICATION QUEUE */}
      {activeTab === 'farms' && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-amber-50 text-amber-950 uppercase font-bold border-b">
              <tr>
                <th className="p-3">Farm Name</th>
                <th className="p-3">Location</th>
                <th className="p-3">Organic Cert Body & Number</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {farmsQueue.map((f) => (
                <tr key={f.id} className="hover:bg-gray-50">
                  <td className="p-3 font-bold text-gray-900">{f.farm_name}</td>
                  <td className="p-3">{f.town}, Co. {f.county}</td>
                  <td className="p-3 font-semibold text-emerald-800">{f.organic_cert_body} ({f.organic_cert_number})</td>
                  <td className="p-3">
                    <button onClick={()=>handleVerifyFarm(f.id, true)} className="px-3 py-1 bg-emerald-700 text-white font-bold rounded text-xs hover:bg-emerald-800">
                      Approve Organic Certification
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 3: IMMUTABLE AUDIT LOG */}
      {activeTab === 'audit' && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-100 text-gray-700 uppercase font-bold border-b">
              <tr>
                <th className="p-3">Timestamp</th>
                <th className="p-3">Action Event</th>
                <th className="p-3">Order ID</th>
                <th className="p-3">Actor Role</th>
                <th className="p-3">Audit Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="p-3 font-mono text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="p-3 font-bold text-emerald-900">{log.action}</td>
                  <td className="p-3 font-mono text-gray-700">{log.order_id ? `#${log.order_id.substring(0, 8)}` : 'N/A'}</td>
                  <td className="p-3 uppercase text-[10px] font-bold text-gray-500">{log.actor_role || 'system'}</td>
                  <td className="p-3 font-mono text-[10px] text-gray-600">{JSON.stringify(log.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 4: SYSTEM SETTINGS */}
      {activeTab === 'settings' && (
        <form onSubmit={handleSaveSettings} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4 max-w-xl text-xs">
          <div>
            <label className="font-bold text-gray-700 block mb-1">Quality Variance Tolerance (%)</label>
            <input
              type="number"
              step="0.5"
              value={adminSettings.variance_tolerance_percent}
              onChange={e=>setAdminSettings({...adminSettings, variance_tolerance_percent: parseFloat(e.target.value)})}
              className="w-full border p-2.5 rounded-lg font-bold text-emerald-900"
            />
            <span className="text-[10px] text-gray-500 block mt-0.5">Variance above this % threshold automatically flags an open dispute</span>
          </div>

          <div>
            <label className="font-bold text-gray-700 block mb-1">Minimum Listing Quality Grade</label>
            <select
              value={adminSettings.min_listing_grade}
              onChange={e=>setAdminSettings({...adminSettings, min_listing_grade: e.target.value})}
              className="w-full border p-2.5 rounded-lg font-semibold"
            >
              <option value="C">Grade C (Grade R rejected)</option>
              <option value="B">Grade B (Grade C & R rejected)</option>
            </select>
          </div>

          <button type="submit" className="px-6 py-2.5 bg-emerald-700 text-white font-bold rounded-xl hover:bg-emerald-800 shadow">
            Save System Platform Settings
          </button>
        </form>
      )}
    </div>
  );
};

export default AdminDashboard;
