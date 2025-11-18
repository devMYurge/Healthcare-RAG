import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Header from './components/Header';
import StatsPanel from './components/StatsPanel';
import { getHealthStatus, getStats } from './services/api';
import './App.css';

function App() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check backend health on mount
    const checkHealth = async () => {
      try {
        const health = await getHealthStatus();
        setHealthStatus(health);
        
        if (health.rag_initialized) {
          const statsData = await getStats();
          setStats(statsData);
        }
      } catch (error) {
        console.error('Failed to check backend health:', error);
        setHealthStatus({ status: 'error', message: error.message });
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <div className="App">
      <Header />
      
      <main className="main-content">
        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Connecting to MedLinkAI...</p>
          </div>
        ) : healthStatus?.status === 'error' ? (
          <div className="error-container">
            <h2>⚠️ Backend Connection Error</h2>
            <p>Could not connect to the MedLinkAI backend API. Please ensure the backend server is running.</p>
            <code>cd backend && uvicorn backend.app.main:app --reload</code>
          </div>
        ) : (
          <div className="content-grid centered">
            <div className="chat-section centered-card">
              <ChatInterface />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
