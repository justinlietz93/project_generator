import React from 'react';
import { Container, Title, Text } from '@mantine/core';

const SubscriptionCancel = () => {
  return (
    <Container size="md" py="xl">
      <Title order={1}>Subscription Canceled</Title>
      <Text>Your subscription has been canceled.</Text>
    </Container>
  );
};

export default SubscriptionCancel; 