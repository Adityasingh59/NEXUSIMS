import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ItemTypes } from './pages/ItemTypes';
import { Skus } from './pages/Skus';
import { Locations } from './pages/Locations';
import { Transactions } from './pages/Transactions';
import { Transfers } from './pages/Transfers';
import { Warehouses } from './pages/Warehouses';
import { Boms } from './pages/Boms';
import { AssemblyOrders } from './pages/AssemblyOrders';
import { SalesOrders } from './pages/SalesOrders';
import { PurchaseOrders } from './pages/PurchaseOrders';
import { Dashboard } from './pages/Dashboard';
import { Reports } from './pages/Reports';
import { Scanner } from './pages/Scanner';
import { ApiKeys } from './pages/ApiKeys';
import { Users } from './pages/Users';
import Login from './pages/Login';
import AcceptInvitation from './pages/AcceptInvitation';
import { useAuthStore } from './stores/useAuthStore';
import './App.css';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuth = useAuthStore((s) => s.isAuthenticated);
  if (!isAuth) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/accept-invitation" element={<AcceptInvitation />} />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="scanner" element={<Scanner />} />

          <Route path="item-types" element={<ItemTypes />} />
          <Route path="skus" element={<Skus />} />
          <Route path="warehouses" element={<Warehouses />} />
          <Route path="locations" element={<Locations />} />
          <Route path="transfers" element={<Transfers />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="boms" element={<Boms />} />
          <Route path="assembly-orders" element={<AssemblyOrders />} />
          <Route path="sales-orders" element={<SalesOrders />} />
          <Route path="purchase-orders" element={<PurchaseOrders />} />
          <Route path="users" element={<Users />} />
          <Route path="api-keys" element={<ApiKeys />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
