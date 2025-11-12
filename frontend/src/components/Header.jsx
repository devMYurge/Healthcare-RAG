import React from 'react';
import './Header.css';

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">🏥</span>
          <h1>Healthcare RAG</h1>
        </div>
        <p className="tagline">AI-Powered Medical Information Retrieval</p>
      </div>
    </header>
  );
}

export default Header;
