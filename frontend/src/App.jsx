import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Marketplace from './pages/Marketplace';
import ProductDetail from './pages/ProductDetail';
import FarmProfile from './pages/FarmProfile';
import FarmerDashboard from './pages/FarmerDashboard';
import FarmerProduction from './pages/FarmerProduction';
import FarmerContracts from './pages/FarmerContracts';
import FarmerNewListing from './pages/FarmerNewListing';
import FarmerHubs from './pages/FarmerHubs';
import FarmerSalesHistory from './pages/FarmerSalesHistory';
import BuyerDashboard from './pages/BuyerDashboard';
import OrderDetail from './pages/OrderDetail';
import Messages from './pages/Messages';
import AdminDashboard from './pages/AdminDashboard';
import Profile from './pages/Profile';
import PublicProfile from './pages/PublicProfile';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900 font-sans">
          <Navbar />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Navigate to="/marketplace" replace />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/marketplace" element={<Marketplace />} />
              <Route path="/product/:id" element={<ProductDetail />} />
              <Route path="/farm/:id" element={<FarmProfile />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/users/:id" element={<PublicProfile />} />

              {/* Farmer Routes */}
              <Route path="/farmer/dashboard" element={<FarmerDashboard />} />
              <Route path="/farmer/production" element={<FarmerProduction />} />
              <Route path="/farmer/contracts" element={<FarmerContracts />} />
              <Route path="/farmer/listings/new" element={<FarmerNewListing />} />
              <Route path="/farmer/hubs" element={<FarmerHubs />} />
              <Route path="/farmer/sales-history" element={<FarmerSalesHistory />} />

              {/* Buyer & Shared Routes */}
              <Route path="/buyer/dashboard" element={<BuyerDashboard />} />
              <Route path="/orders/:id" element={<OrderDetail />} />
              <Route path="/messages" element={<Messages />} />

              {/* Admin Routes */}
              <Route path="/admin" element={<AdminDashboard />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
