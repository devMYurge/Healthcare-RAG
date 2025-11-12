import React from 'react';
import './StatsPanel.css';

function StatsPanel({ stats }) {
  if (!stats) {
    return (
      <div className="stats-panel">
        <h3>System Status</h3>
        <p className="loading-text">Loading statistics...</p>
      </div>
    );
  }

  return (
    <div className="stats-panel">
      <h3>System Statistics</h3>
      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-value">{stats.document_count || 0}</div>
          <div className="stat-label">Documents</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">
            <span className={`status-badge ${stats.status}`}>
              {stats.status === 'active' ? '🟢' : '🔴'}
            </span>
          </div>
          <div className="stat-label">Status</div>
        </div>
      </div>
      {stats.embedding_model && (
        <div className="model-info">
          <p className="model-label">Embedding Model:</p>
          <p className="model-name">{stats.embedding_model}</p>
        </div>
      )}
    </div>
  );
}

export default StatsPanel;
