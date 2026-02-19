import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ItemTypes } from './pages/ItemTypes';
import { Skus } from './pages/Skus';
import { Locations } from './pages/Locations';
import { Transactions } from './pages/Transactions';
import { Transfers } from './pages/Transfers';
import { Warehouses } from './pages/Warehouses';
import './App.css';

function Home() {
  return (
    <div className="page">
      <h1>NEXUS IMS</h1>
      <p>Rigid Accuracy. Infinite Flexibility.</p>
      <a href="/api/v1/docs" target="_blank" rel="noopener noreferrer">API Docs</a>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="item-types" element={<ItemTypes />} />
          <Route path="skus" element={<Skus />} />
          <Route path="warehouses" element={<Warehouses />} />
          <Route path="locations" element={<Locations />} />
          <Route path="transfers" element={<Transfers />} />
          <Route path="transactions" element={<Transactions />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
