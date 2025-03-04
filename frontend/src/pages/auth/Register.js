import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Container, 
  Title, 
  TextInput, 
  PasswordInput, 
  Button, 
  Text, 
  Paper, 
  Divider, 
  Anchor,
  Loader,
  Checkbox,
  Stack
} from '@mantine/core';
import { useAuth } from '../../context/AuthContext';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const validateEmail = (email) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Basic validation
    if (!username.trim() || !email.trim() || !password.trim()) {
      setError('All fields are required');
      return;
    }
    
    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }
    
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    if (!acceptTerms) {
      setError('You must accept the terms and conditions');
      return;
    }
    
    setLoading(true);
    
    try {
      const success = await register(username, email, password);
      if (success) {
        // Redirect to login or pricing page
        navigate('/pricing');
      }
    } catch (err) {
      setError('An error occurred during registration. Please try again.');
      console.error('Registration error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size="xs" py="xl">
      <Paper radius="md" p="xl" withBorder>
        <Title order={2} align="center" mb="md">
          Create an Account
        </Title>
        <Text color="dimmed" size="sm" align="center" mb="lg">
          Sign up to access AI models through our unified API
        </Text>

        <form onSubmit={handleSubmit}>
          <Stack spacing="md">
            <TextInput
              label="Username"
              placeholder="Choose a username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />

            <TextInput
              label="Email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              type="email"
            />

            <PasswordInput
              label="Password"
              placeholder="Choose a password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            
            <PasswordInput
              label="Confirm Password"
              placeholder="Repeat your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
            
            <Checkbox
              label="I agree to the terms and conditions"
              checked={acceptTerms}
              onChange={(e) => setAcceptTerms(e.target.checked)}
              required
            />

            {error && (
              <Text color="red" size="sm">
                {error}
              </Text>
            )}

            <Button fullWidth type="submit" disabled={loading}>
              {loading ? <Loader size="sm" /> : "Register"}
            </Button>
          </Stack>
        </form>

        <Divider my="lg" />

        <Text align="center" mt="md">
          Already have an account?{' '}
          <Anchor component={Link} to="/login">
            Log in
          </Anchor>
        </Text>
      </Paper>
    </Container>
  );
};

export default Register; 