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
            <p>Connecting to Healthcare RAG system...</p>
          </div>
        ) : healthStatus?.status === 'error' ? (
          <div className="error-container">
            <h2>⚠️ Backend Connection Error</h2>
            <p>Could not connect to the backend API. Please ensure the backend server is running.</p>
            <code>cd backend && uvicorn app.main:app --reload</code>
          </div>
        ) : (
          <div className="content-grid">
            <div className="chat-section">
              <ChatInterface />
            </div>
            <div className="sidebar">
              <StatsPanel stats={stats} />
              <div className="info-panel">
                <h3>About Healthcare RAG</h3>
                <p>
                  This AI-powered system uses Retrieval-Augmented Generation (RAG) 
                  to provide accurate healthcare information by searching through 
                  a curated medical knowledge base.
                </p>
                <div className="features">
                  <div className="feature">
                    <span className="feature-icon">🔍</span>
                    <span>Semantic Search</span>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">🤖</span>
                    <span>AI-Powered Responses</span>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">📚</span>
                    <span>Evidence-Based</span>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">⚡</span>
                    <span>Real-Time Results</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
