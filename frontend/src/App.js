import React from "react";
import { BrowserRouter as Router, Routes, Route, NavLink } from "react-router-dom";
import ChatWindow from "./components/ChatWindow";
import Dashboard from "./components/Dashboard";
import "./App.css";

export default function App() {
  return (
    <Router>
      <div className="app-shell">
        <nav className="top-nav">
          <div className="brand">EthicaMind</div>
          <div className="nav-links">
            <NavLink to="/" end className={({isActive}) => isActive ? "link active" : "link"}>
              Chat
            </NavLink>
            <NavLink to="/insights" className={({isActive}) => isActive ? "link active" : "link"}>
              Insights
            </NavLink>
          </div>
        </nav>

        <main className="main-area">
          <Routes>
            <Route path="/" element={<ChatWindow />} />
            <Route path="/insights" element={<Dashboard />} />
          </Routes>
        </main>

        <footer className="footer">
          <small>EthicaMind Prototype — Responsible wellness assistant</small>
        </footer>
      </div>
    </Router>
  );
}
