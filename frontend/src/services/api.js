import axios from 'axios';

const API_BASE = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Configure axios defaults
axios.defaults.baseURL = API_BASE;

// Add request interceptor to include auth token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('steam_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle auth errors
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('steam_token');
      localStorage.removeItem('steam_user');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const steamAPI = {
  // Authentication
  getSteamLoginUrl: () => axios.get('/api/auth/steam/login'),
  
  // User profile
  getProfile: () => axios.get('/api/user/profile'),
  
  // Inventory
  getInventory: () => axios.get('/api/user/inventory'),
  
  // Balance
  addBalance: (amount) => axios.post('/api/user/balance/add', { amount }),
  
  // Cases
  getCases: () => axios.get('/api/cases'),
  openCase: (caseId) => axios.post(`/api/cases/${caseId}/open`),
  
  // Crypto Payment methods
  getExchangeRate: () => axios.get('/api/exchange-rate'),
  createCryptoPayment: (paymentData) => axios.post('/api/create-crypto-payment', paymentData),
  applyPromoCode: (promoData) => axios.post('/api/apply-promocode', promoData),
  getUserTransactions: () => axios.get('/api/user/transactions'),
  testCryptoBot: () => axios.get('/api/test-crypto-bot'),
  
  // Utility
  getToken: () => localStorage.getItem('steam_token'),
  getUser: () => {
    const user = localStorage.getItem('steam_user');
    return user ? JSON.parse(user) : null;
  },
  isAuthenticated: () => !!localStorage.getItem('steam_token'),
  logout: () => {
    localStorage.removeItem('steam_token');
    localStorage.removeItem('steam_user');
  }
};

export default steamAPI;