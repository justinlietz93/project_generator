import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Container, 
  Title, 
  TextInput, 
  PasswordInput, 
  Button, 
  Group, 
  Text, 
  Paper, 
  Divider, 
  Center, 
  Box, 
  Anchor,
  Loader
} from '@mantine/core';
import { useAuth } from '../../context/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    if (!username.trim() || !password.trim()) {
      setError('Username and password are required');
      setLoading(false);
      return;
    }
    
    try {
      const success = await login(username, password);
      if (success) {
        navigate('/');
      } else {
        setError('Invalid credentials');
      }
    } catch (err) {
      setError('An error occurred during login. Please try again.');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Demo credentials for easy testing
  const setDemoCredentials = () => {
    setUsername('demo');
    setPassword('password123');
  };

  return (
    <Container size="xs" py="xl">
      <Paper radius="md" p="xl" withBorder>
        <Title order={2} align="center" mb="md">
          Welcome to Scry AI Project Builder
        </Title>
        <Text color="dimmed" size="sm" align="center" mb="lg">
          Build entire projects with one prompt
        </Text>

        <form onSubmit={handleSubmit}>
          <TextInput
            label="Username"
            placeholder="Your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            mb="md"
          />

          <PasswordInput
            label="Password"
            placeholder="Your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            mb="xl"
          />

          {error && (
            <Text color="red" size="sm" mb="md">
              {error}
            </Text>
          )}

          <Button fullWidth type="submit" disabled={loading}>
            {loading ? <Loader size="sm" /> : "Sign in"}
          </Button>
        </form>

        <Divider label="or" labelPosition="center" my="lg" />

        <Center>
          <Button variant="subtle" onClick={setDemoCredentials}>
            Use demo credentials
          </Button>
        </Center>

        <Text align="center" mt="md">
          Don't have an account?{' '}
          <Anchor component={Link} to="/register">
            Register
          </Anchor>
        </Text>
        
        {/* Display demo credentials for easier testing */}
        <Box mt="xl" p="xs" sx={(theme) => ({ 
          backgroundColor: theme.colors.gray[0],
          borderRadius: theme.radius.sm,
        })}>
          <Text size="xs" color="dimmed" align="center">
            Demo credentials:
            <br />
            Username: demo | Password: password123
          </Text>
        </Box>
      </Paper>
    </Container>
  );
};

export default Login; 