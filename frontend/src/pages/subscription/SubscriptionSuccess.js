import React from 'react';
import { Container, Title, Text } from '@mantine/core';

const SubscriptionSuccess = () => {
  return (
    <Container size="md" py="xl">
      <Title order={1}>Subscription Successful</Title>
      <Text>Your subscription has been successfully activated.</Text>
    </Container>
  );
};

export default SubscriptionSuccess; 