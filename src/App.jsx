import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink, Outlet } from 'react-router-dom';
import ProductList from './components/ProductList';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <nav className="navbar">
            <div className="navbar-brand">
              <Link to="/">Pharmacy ERP</Link>
            </div>
            <ul className="navbar-menu">
              <li><NavLink to="/dashboard" end>Dashboard</NavLink></li>
              <li><NavLink to="/inventory">Inventory</NavLink></li>
              <li><NavLink to="/sales">Sales</NavLink></li>
              <li><NavLink to="/purchases">Purchases</NavLink></li>
              <li><NavLink to="/customers">Customers</NavLink></li>
              <li><NavLink to="/suppliers">Suppliers</NavLink></li>
              <li><NavLink to="/reports">Reports</NavLink></li>
            </ul>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/sales" element={<Sales />} />
            <Route path="/purchases" element={<Purchases />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

// Placeholder components
function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the Pharmacy ERP System</p>
    </div>
  );
}

function Inventory() {
  return (
    <div>
      <h1>Inventory Management</h1>
      <ProductList />
    </div>
  );
}

function Sales() {
  return (
    <div>
      <h1>Sales & Billing</h1>
      <p>Process sales and generate bills.</p>
    </div>
  );
}

function Purchases() {
  return (
    <div>
      <h1>Purchase Management</h1>
      <p>Manage purchase orders and supplier invoices.</p>
    </div>
  );
}

function Customers() {
  return (
    <div>
      <h1>Customer Management</h1>
      <p>Maintain customer records and history.</p>
    </div>
  );
}

function Suppliers() {
  return (
    <div>
      <h1>Supplier Management</h1>
      <p>Maintain supplier records and contacts.</p>
    </div>
  );
}

function Reports() {
  return (
    <div>
      <h1>Reports</h1>
      <p>View various reports and analytics.</p>
    </div>
  );
}

function NotFound() {
  return (
    <div>
      <h1>404 - Page Not Found</h1>
      <p>The page you are looking for does not exist.</p>
    </div>
  );
}

export default App;