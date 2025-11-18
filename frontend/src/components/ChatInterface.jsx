import React, { useState, useRef, useEffect } from 'react';
import { queryHealthcare } from '../services/api';
import ReactMarkdown from 'react-markdown';
import './ChatInterface.css';

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      content: 'Hello! I\'m MedLinkAI — your guide for finding recommended doctors, explaining medical jargon, and learning about diseases. How can I help you today?',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      type: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await queryHealthcare(input);
      
      const assistantMessage = {
        type: 'assistant',
        content: response.answer,
        sources: response.sources,
        confidence: response.confidence,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        type: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const suggestedQuestions = [
    'Find a recommended doctor for hypertension',
    'Explain the medical term: bradycardia',
    'What are the symptoms and treatment of asthma?',
    'How do I choose a specialist for chronic kidney disease?'
  ];

  const handleSuggestionClick = (question) => {
    setInput(question);
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    setUploadedFiles(files);
  };

  return (
    <div className="chat-interface">
      <div className="chat-container">
        <div className="messages-container">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.type}`}>
              <div className="message-avatar">
                {message.type === 'user' ? '👤' : message.type === 'error' ? '⚠️' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-text">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div className="sources">
                    <p className="sources-title">📚 Sources:</p>
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="source-item">
                        <div className="source-content">{source.content}</div>
                        {source.metadata && (
                          <div className="source-metadata">
                            {source.metadata.condition && (
                              <span className="metadata-tag">
                                Condition: {source.metadata.condition}
                              </span>
                            )}
                            {source.metadata.category && (
                              <span className="metadata-tag">
                                Category: {source.metadata.category}
                              </span>
                            )}
                            <span className="relevance-score">
                              Relevance: {(source.relevance_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {message.confidence !== undefined && (
                  <div className="confidence-bar">
                    <div className="confidence-label">
                      Confidence: {(message.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="confidence-fill" style={{ width: `${message.confidence * 100}%` }} />
                  </div>
                )}
                <div className="message-timestamp">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant loading">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
          <div className="bottom-controls">
            <div className="file-upload">
              <label className="file-label">
                📎 Attach files
                <input type="file" multiple onChange={handleFileChange} />
              </label>
              <div className="uploaded-list">
                {uploadedFiles.map((f, i) => (
                  <div key={i} className="uploaded-item">{f.name}</div>
                ))}
              </div>
            </div>

            <form className="input-form" onSubmit={handleSubmit}>
              <input
                type="text"
                className="message-input"
                placeholder="Ask MedLinkAI... (e.g. 'Find a cardiologist near me')"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
              />
              <button
                type="submit"
                className="send-button"
                disabled={!input.trim() || isLoading}
              >
                {isLoading ? '⏳' : '📤'}
              </button>
            </form>
          </div>
      </div>
    </div>
  );
}

export default ChatInterface;
