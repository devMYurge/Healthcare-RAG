import React, { useState, useRef, useEffect } from 'react';
import { queryHealthcare } from '../services/api';
import ReactMarkdown from 'react-markdown';
import './ChatInterface.css';

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      content: 'Hello! I\'m your Healthcare AI assistant. I can help answer questions about various medical conditions, treatments, and health topics. What would you like to know?',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
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
    'What is hypertension and how is it treated?',
    'Tell me about Type 2 diabetes management',
    'What are the symptoms of asthma?',
    'How is depression treated?',
  ];

  const handleSuggestionClick = (question) => {
    setInput(question);
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

        {messages.length === 1 && (
          <div className="suggestions">
            <p className="suggestions-title">Try asking:</p>
            <div className="suggestions-grid">
              {suggestedQuestions.map((question, index) => (
                <button
                  key={index}
                  className="suggestion-button"
                  onClick={() => handleSuggestionClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            className="message-input"
            placeholder="Ask a healthcare question..."
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
  );
}

export default ChatInterface;
