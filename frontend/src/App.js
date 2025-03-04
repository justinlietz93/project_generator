import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

// Layout
import AppLayout from './components/layout/AppLayout';

// Auth & User Management
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Profile from './pages/user/Profile';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Main App Features
import Dashboard from './pages/Dashboard';
import Playground from './pages/Playground';
import Usage from './pages/Usage';
import ProjectBuilder from './pages/ProjectBuilder';

// Subscription & Payment
import Pricing from './pages/subscription/Pricing';
import SubscriptionSuccess from './pages/subscription/SubscriptionSuccess';
import SubscriptionCancel from './pages/subscription/SubscriptionCancel';

// Auth Context Provider
import { AuthProvider } from './context/AuthContext';

// Custom theme
const theme = createTheme({
  primaryColor: 'violet',
  primaryShade: 6,
  fontFamily: 'Inter, sans-serif',
  headings: {
    fontFamily: 'Inter, sans-serif',
  },
  colors: {
    // Custom violet shade
    violet: [
      '#f5f0ff',
      '#e5d9fa',
      '#d0b9f0',
      '#b795e6',
      '#9f71dc',
      '#8c56d0',
      '#7b3dc7',
      '#6930b0',
      '#5a2799',
      '#4a1f82'
    ],
    // Custom dark theme colors
    dark: [
      '#C1C2C5',
      '#A6A7AB',
      '#909296',
      '#5c5f66',
      '#373A40',
      '#2C2E33',
      '#25262b',
      '#1A1B1E',
      '#141517',
      '#101113',
    ],
  },
  components: {
    Button: {
      defaultProps: {
        color: 'violet',
      },
    },
  },
});

// Update document title
document.title = "Scry AI Project Builder";

function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Notifications position="top-right" />
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Main App Routes (Protected) */}
            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/playground" element={<Playground />} />
              <Route path="/project-builder" element={<ProjectBuilder />} />
              <Route path="/usage" element={<Usage />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/subscription/success" element={<SubscriptionSuccess />} />
              <Route path="/subscription/cancel" element={<SubscriptionCancel />} />
            </Route>

            {/* Redirect for unmatched routes */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </MantineProvider>
  );
}

export default App; 