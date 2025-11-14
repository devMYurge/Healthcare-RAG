import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getHealthStatus = async () => {
  try {
    const response = await api.get('/api/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};

export const getStats = async () => {
  try {
    const response = await api.get('/api/stats');
    return response.data;
  } catch (error) {
    console.error('Failed to get stats:', error);
    throw error;
  }
};

export const queryHealthcare = async (question, maxResults = 3) => {
  try {
    const response = await api.post('/api/query', {
      question,
      max_results: maxResults,
    });
    return response.data;
  } catch (error) {
    console.error('Query failed:', error);
    throw error;
  }
};

export const addDocument = async (content, metadata = {}) => {
  try {
    const response = await api.post('/api/documents', {
      content,
      metadata,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to add document:', error);
    throw error;
  }
};

export default api;
