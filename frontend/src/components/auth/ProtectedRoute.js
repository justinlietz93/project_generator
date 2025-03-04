import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Loader, Center, Paper, Text, Box } from '@mantine/core';

/**
 * Protected Route Component
 * 
 * Redirects to login if user is not authenticated
 * Shows loading state while authentication is being checked
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <Center style={{ height: '100vh', width: '100vw' }}>
        <Paper shadow="md" p="xl" radius="md">
          <Box style={{ textAlign: 'center' }}>
            <Loader size="lg" variant="dots" mb="md" />
            <Text>Authenticating...</Text>
          </Box>
        </Paper>
      </Center>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Render children if authenticated
  return children;
};

export default ProtectedRoute; 