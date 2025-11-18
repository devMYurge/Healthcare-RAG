import React from 'react';
import './Header.css';

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">🔗</span>
          <h1>MedLinkAI</h1>
        </div>
        <p className="tagline">Trusted RAG for doctor recommendations, medical jargon, and disease info</p>
      </div>
    </header>
  );
}

export default Header;
