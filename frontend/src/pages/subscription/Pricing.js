import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Title,
  Text,
  Group,
  Button,
  Grid,
  Card,
  Badge,
  List,
  ThemeIcon,
  Divider,
  Box,
  Alert,
  Loader,
  Center
} from '@mantine/core';
import { IconCheck, IconX, IconCreditCard, IconInfoCircle } from '@tabler/icons-react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { notifications } from '@mantine/notifications';

// Load Stripe outside of component to avoid recreating on re-renders
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLIC_KEY || 'pk_test_sample');

// Subscription plans data
const plans = [
  {
    id: 'standard',
    name: 'Standard',
    price: '$19.99',
    description: 'Perfect for individual users and small projects',
    features: [
      'Access to Claude 3.7 Sonnet and DeepSeek models',
      'Max 10 requests per minute',
      'Token limit of 2,000 per request',
      '10% discount on pay-as-you-go rates',
      'Basic support'
    ],
    notIncluded: [
      'Access to Gemini and Ollama models',
      'Advanced token rates'
    ]
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '$49.99',
    description: 'For professionals and businesses with higher needs',
    features: [
      'Access to ALL models (Claude, DeepSeek, Gemini, Ollama)',
      'Max 30 requests per minute',
      'Token limit of 8,000 per request',
      '25% discount on pay-as-you-go rates',
      'Priority support',
      'API key for programmatic access'
    ],
    recommended: true
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Contact Us',
    description: 'Custom solutions for large-scale use',
    features: [
      'Custom model selection',
      'Unlimited requests (fair use policy)',
      'Custom token limits',
      '40% discount on pay-as-you-go rates',
      'Dedicated support',
      'SLA guarantees',
      'On-premise deployment options'
    ],
    contact: true
  }
];

// CheckoutForm component for handling payments
const CheckoutForm = ({ plan, onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user } = useAuth();

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Simulated subscription creation since we don't have a real backend yet
      // In production, you would make an API call to your backend
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Simulate success
      onSuccess();
      
      /* In production with real backend:
      
      // Get payment method
      const { error: stripeError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: elements.getElement(CardElement),
      });

      if (stripeError) {
        setError(stripeError.message);
        return;
      }

      // Create subscription on your server
      const response = await axios.post('/subscription', {
        plan: plan.id,
        payment_method_id: paymentMethod.id,
      });

      const { client_secret } = response.data;

      // Confirm payment with Stripe
      const { error: confirmError } = await stripe.confirmCardPayment(client_secret);

      if (confirmError) {
        setError(confirmError.message);
      } else {
        onSuccess();
      }
      */
      
    } catch (err) {
      console.error('Subscription error:', err);
      setError('An error occurred while processing your payment');
      onError('Payment processing failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Box mb="lg">
        <Text weight={500} mb="xs">Card Details</Text>
        <Box style={{ border: '1px solid #ced4da', borderRadius: '4px', padding: '10px' }}>
          <CardElement options={{
            style: {
              base: {
                fontSize: '16px',
                color: '#424770',
                '::placeholder': {
                  color: '#aab7c4',
                },
              },
              invalid: {
                color: '#9e2146',
              },
            },
          }} />
        </Box>
      </Box>

      {error && (
        <Alert color="red" title="Payment Error" icon={<IconInfoCircle />} mb="md">
          {error}
        </Alert>
      )}

      <Button 
        type="submit" 
        fullWidth
        leftIcon={<IconCreditCard size={16} />}
        loading={loading}
        disabled={!stripe || loading}
      >
        Subscribe to {plan.name}
      </Button>
    </form>
  );
};

// Main Pricing component
const Pricing = () => {
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [showCheckout, setShowCheckout] = useState(false);
  const [checkoutSuccess, setCheckoutSuccess] = useState(false);
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  const handleSelectPlan = (plan) => {
    if (plan.contact) {
      // Handle enterprise plan contact request
      window.location.href = 'mailto:sales@yourcompany.com?subject=Enterprise Plan Inquiry';
      return;
    }
    
    setSelectedPlan(plan);
    setShowCheckout(true);
  };

  const handleCheckoutSuccess = async () => {
    setCheckoutSuccess(true);
    await refreshUser();
    
    notifications.show({
      title: 'Subscription Successful',
      message: `You've successfully subscribed to our ${selectedPlan.name} plan!`,
      color: 'green'
    });
    
    // Navigate to success page after delay
    setTimeout(() => {
      navigate('/subscription/success');
    }, 2000);
  };

  const handleCheckoutError = (errorMessage) => {
    notifications.show({
      title: 'Subscription Failed',
      message: errorMessage || 'There was a problem with your subscription. Please try again.',
      color: 'red'
    });
  };

  return (
    <Container size="lg" py="xl">
      <Title order={1} align="center" mb="sm">Choose Your Plan</Title>
      <Text align="center" color="dimmed" mb="xl" size="lg">
        Select the plan that best fits your AI generation needs
      </Text>

      {checkoutSuccess ? (
        <Center py="xl">
          <Box style={{ textAlign: 'center' }}>
            <ThemeIcon size={60} radius="xl" color="green" mb="md">
              <IconCheck size={30} />
            </ThemeIcon>
            <Title order={2} mb="md">Subscription Successful!</Title>
            <Text mb="lg">
              You've successfully subscribed to our {selectedPlan?.name} plan.
              Redirecting you to the subscription confirmation page...
            </Text>
            <Loader variant="dots" />
          </Box>
        </Center>
      ) : showCheckout && selectedPlan ? (
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }} offset={{ md: 3 }}>
            <Card shadow="sm" p="lg" radius="md" withBorder>
              <Group position="apart" mb="md">
                <div>
                  <Title order={3}>{selectedPlan.name} Plan</Title>
                  <Text weight={700} size="xl" color="indigo">{selectedPlan.price}/month</Text>
                </div>
                <Button variant="subtle" onClick={() => setShowCheckout(false)}>
                  Back to Plans
                </Button>
              </Group>

              <Divider my="md" />

              <Elements stripe={stripePromise}>
                <CheckoutForm 
                  plan={selectedPlan} 
                  onSuccess={handleCheckoutSuccess} 
                  onError={handleCheckoutError}
                />
              </Elements>
            </Card>
          </Grid.Col>
        </Grid>
      ) : (
        <Grid>
          {plans.map((plan) => (
            <Grid.Col key={plan.id} span={{ base: 12, sm: 6, md: 4 }}>
              <Card 
                shadow="sm" 
                p="lg" 
                radius="md" 
                withBorder 
                style={{ 
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderColor: plan.recommended ? '#4263eb' : undefined,
                  borderWidth: plan.recommended ? '2px' : '1px'
                }}
              >
                {plan.recommended && (
                  <Badge color="indigo" variant="filled" style={{ position: 'absolute', top: 10, right: 10 }}>
                    Recommended
                  </Badge>
                )}
                
                <Title order={3} mb="xs">{plan.name}</Title>
                <Text weight={700} size="xl" color="indigo" mb="md">{plan.price}</Text>
                <Text size="sm" color="dimmed" mb="md">{plan.description}</Text>
                
                <Divider my="md" />
                
                <List 
                  spacing="sm" 
                  size="sm" 
                  center 
                  icon={
                    <ThemeIcon color="teal" size={20} radius="xl">
                      <IconCheck size={12} />
                    </ThemeIcon>
                  }
                  mb="md"
                >
                  {plan.features.map((feature, index) => (
                    <List.Item key={index}>
                      {feature}
                    </List.Item>
                  ))}
                </List>

                {plan.notIncluded && (
                  <>
                    <Text size="sm" weight={500} mb="xs">Not included:</Text>
                    <List 
                      spacing="sm" 
                      size="sm" 
                      center 
                      icon={
                        <ThemeIcon color="red" size={20} radius="xl">
                          <IconX size={12} />
                        </ThemeIcon>
                      }
                      mb="md"
                    >
                      {plan.notIncluded.map((feature, index) => (
                        <List.Item key={index}>
                          {feature}
                        </List.Item>
                      ))}
                    </List>
                  </>
                )}
                
                <Box style={{ marginTop: 'auto' }}>
                  <Button 
                    variant={plan.recommended ? "filled" : "outline"}
                    color={plan.recommended ? "indigo" : "gray"}
                    fullWidth
                    onClick={() => handleSelectPlan(plan)}
                  >
                    {plan.contact ? "Contact Sales" : "Subscribe"}
                  </Button>
                </Box>
              </Card>
            </Grid.Col>
          ))}
        </Grid>
      )}
    </Container>
  );
};

export default Pricing; 