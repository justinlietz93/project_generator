import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { notifications } from '@mantine/notifications';

// Create auth context
const AuthContext = createContext();

// Hook for using auth context
export const useAuth = () => useContext(AuthContext);

// Mock user data for development when backend is unavailable
const MOCK_USER = {
  username: 'demo',
  email: 'demo@example.com',
  tier: 'standard'
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [backendAvailable, setBackendAvailable] = useState(true);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          // Set default Authorization header for all requests
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          
          // Fetch current user data
          const response = await axios.get('/user/me');
          setUser(response.data);
          setBackendAvailable(true);
        } catch (err) {
          console.error('Error initializing auth:', err);
          
          // Check if backend is unavailable (connection refused)
          if (err.message && err.message.includes('Network Error')) {
            console.warn('Backend appears to be unavailable, using mock data mode');
            setBackendAvailable(false);
            
            // If we have a token in localStorage from previous mock login, restore the mock user
            if (localStorage.getItem('mock_user')) {
              setUser(JSON.parse(localStorage.getItem('mock_user')));
            } else {
              logout();
            }
          } else if (err.response && (err.response.status === 401 || err.response.status === 403)) {
            // If token is invalid, clear it
            logout();
          }
          
          setError(err.message || 'Authentication failed');
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [token]);

  // Login function
  const login = async (username, password) => {
    try {
      setLoading(true);
      
      // First try with real backend
      if (backendAvailable) {
        try {
          // Format data for token endpoint (OAuth2 format)
          const formData = new FormData();
          formData.append('username', username);
          formData.append('password', password);
          
          // Get token
          const response = await axios.post('/token', formData);
          const { access_token } = response.data;
          
          // Save token and set default header
          localStorage.setItem('token', access_token);
          setToken(access_token);
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          // Fetch user data
          const userResponse = await axios.get('/user/me');
          setUser(userResponse.data);
          
          // Success notification
          notifications.show({
            title: 'Login Successful',
            message: `Welcome back, ${userResponse.data.username}!`,
            color: 'green'
          });
          
          return true;
        } catch (err) {
          // If we get a network error, switch to mock mode
          if (err.message && err.message.includes('Network Error')) {
            console.warn('Backend appears to be unavailable, switching to mock authentication');
            setBackendAvailable(false);
            // Continue to mock auth flow
          } else {
            // Other error, re-throw to be caught by outer catch
            throw err;
          }
        }
      }
      
      // If backend is unavailable or network error occurred, use mock auth
      if (!backendAvailable) {
        // Check mock credentials
        if (username === 'demo' && password === 'password123') {
          // Create a fake token
          const mockToken = 'mock_' + Math.random().toString(36).substring(2);
          localStorage.setItem('token', mockToken);
          localStorage.setItem('mock_user', JSON.stringify(MOCK_USER));
          setToken(mockToken);
          setUser(MOCK_USER);
          
          // Success notification
          notifications.show({
            title: 'Demo Login Successful',
            message: 'You are now logged in with demo credentials',
            color: 'green'
          });
          
          return true;
        } else {
          throw new Error('Invalid credentials for mock authentication');
        }
      }
      
      return false;
    } catch (err) {
      console.error('Login error:', err);
      setError(err.response?.data?.detail || err.message || 'Login failed');
      
      // Error notification
      notifications.show({
        title: 'Login Failed',
        message: err.response?.data?.detail || 'Invalid credentials',
        color: 'red'
      });
      
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (username, email, password) => {
    try {
      setLoading(true);
      
      // If backend is available, try normal registration
      if (backendAvailable) {
        try {
          // Register new user
          await axios.post('/register', { username, email, password });
          
          // Success notification
          notifications.show({
            title: 'Registration Successful',
            message: 'Your account has been created. You can now log in.',
            color: 'green'
          });
          
          return true;
        } catch (err) {
          // If we get a network error, switch to mock mode
          if (err.message && err.message.includes('Network Error')) {
            console.warn('Backend appears to be unavailable, switching to mock registration');
            setBackendAvailable(false);
            // Continue to mock registration flow
          } else {
            // Other error, re-throw to be caught by outer catch
            throw err;
          }
        }
      }
      
      // If backend is unavailable, use mock registration
      if (!backendAvailable) {
        // Always succeed for simplicity
        notifications.show({
          title: 'Demo Registration Successful',
          message: 'Your demo account has been created. You can now log in with username: "demo" and password: "password123"',
          color: 'green'
        });
        
        return true;
      }
      
      return false;
    } catch (err) {
      console.error('Registration error:', err);
      setError(err.response?.data?.detail || err.message || 'Registration failed');
      
      // Error notification
      notifications.show({
        title: 'Registration Failed',
        message: err.response?.data?.detail || 'Could not create account',
        color: 'red'
      });
      
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('mock_user');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
    
    // Notification
    notifications.show({
      title: 'Logged Out',
      message: 'You have been successfully logged out.',
      color: 'blue'
    });
  };

  // Refresh user data
  const refreshUser = async () => {
    if (!token) return;
    
    if (backendAvailable) {
      try {
        const response = await axios.get('/user/me');
        setUser(response.data);
      } catch (err) {
        console.error('Error refreshing user data:', err);
        
        // Check if backend is unavailable
        if (err.message && err.message.includes('Network Error')) {
          setBackendAvailable(false);
          
          // If we have mock user data, use it
          if (localStorage.getItem('mock_user')) {
            setUser(JSON.parse(localStorage.getItem('mock_user')));
          }
        } else if (err.response && (err.response.status === 401 || err.response.status === 403)) {
          logout();
        }
      }
    } else if (localStorage.getItem('mock_user')) {
      // If backend is unavailable but we have mock data, use it
      setUser(JSON.parse(localStorage.getItem('mock_user')));
    }
  };

  // Check if user has premium access
  const isPremium = () => {
    return user && user.tier === 'premium';
  };

  // Value object to provide through context
  const value = {
    user,
    loading,
    error,
    token,
    login,
    register,
    logout,
    refreshUser,
    isPremium,
    isAuthenticated: !!token,
    isMockMode: !backendAvailable
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}; 