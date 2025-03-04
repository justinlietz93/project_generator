import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container,
  Title,
  Text,
  Textarea,
  Button,
  Group,
  Select,
  Slider,
  Paper,
  Box,
  LoadingOverlay,
  Badge,
  Alert,
  Stack,
  Grid,
  ScrollArea,
  ThemeIcon
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useAuth } from '../context/AuthContext';
import { IconRobot, IconSend, IconInfoCircle, IconAdjustments } from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';

const Playground = () => {
  const { user, isPremium } = useAuth();
  
  // State
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful AI assistant.');
  const [userPrompt, setUserPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [error, setError] = useState(null);
  const [tokensUsed, setTokensUsed] = useState(0);
  const [conversationHistory, setConversationHistory] = useState([]);

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get('/models');
        setAvailableModels(response.data);
        
        // Set a default model if available
        if (response.data.length > 0) {
          setSelectedModel(response.data[0]);
        }
      } catch (err) {
        console.error('Error fetching models:', err);
        setError('Could not load available models. Please try again later.');
      }
    };

    fetchModels();
  }, []);

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!userPrompt.trim()) {
      notifications.show({
        title: 'Empty Prompt',
        message: 'Please enter a prompt before submitting.',
        color: 'yellow'
      });
      return;
    }
    
    if (!selectedModel) {
      notifications.show({
        title: 'No Model Selected',
        message: 'Please select an AI model first.',
        color: 'yellow'
      });
      return;
    }
    
    setLoading(true);
    setError(null);
    
    // Add user message to conversation history
    const newMessage = { role: 'user', content: userPrompt };
    setConversationHistory([...conversationHistory, newMessage]);
    
    try {
      const response = await axios.post('/generate', {
        model: selectedModel,
        system_prompt: systemPrompt,
        user_prompt: userPrompt,
        max_tokens: maxTokens,
        temperature: temperature
      });
      
      setResponse(response.data.response);
      setTokensUsed(response.data.tokens_used);
      
      // Add AI response to conversation history
      const aiMessage = { role: 'assistant', content: response.data.response };
      setConversationHistory([...conversationHistory, newMessage, aiMessage]);
      
      // Clear user prompt for next input
      setUserPrompt('');
    } catch (err) {
      console.error('Error generating response:', err);
      setError(err.response?.data?.detail || 'An error occurred while generating a response.');
      
      notifications.show({
        title: 'Generation Failed',
        message: err.response?.data?.detail || 'Could not generate a response. Please try again.',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  // Clear conversation
  const handleClearConversation = () => {
    setConversationHistory([]);
    setResponse('');
    setUserPrompt('');
    setTokensUsed(0);
  };

  return (
    <Container size="lg" py="xl">
      <Title order={1} mb="md">
        <IconRobot size={30} style={{ marginRight: 10 }} />
        AI Playground
      </Title>
      
      <Text color="dimmed" mb="xl">
        Experiment with different AI models and prompts to generate text responses.
      </Text>
      
      <Grid>
        {/* Left side - Input & Controls */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <form onSubmit={handleSubmit}>
            <Paper shadow="xs" p="md" withBorder mb="md">
              <Stack>
                <Select
                  label="AI Model"
                  placeholder="Select an AI model"
                  data={availableModels.map(model => ({ value: model, label: model }))}
                  value={selectedModel}
                  onChange={setSelectedModel}
                  required
                  description={isPremium() ? 
                    "Premium tier: Access to all models" : 
                    "Upgrade to Premium for access to more models"}
                />
                
                <Textarea
                  label="System Prompt"
                  description="Instructions for the AI model"
                  placeholder="You are a helpful AI assistant."
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  minRows={2}
                  mb="sm"
                />

                <Button 
                  variant="subtle" 
                  rightIcon={<IconAdjustments size={16} />}
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  mb="xs"
                >
                  {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'}
                </Button>
                
                {showAdvanced && (
                  <Box mb="md">
                    <Text size="sm" weight={500} mb={5}>Temperature: {temperature}</Text>
                    <Slider
                      min={0}
                      max={1}
                      step={0.1}
                      label={(value) => value.toFixed(1)}
                      value={temperature}
                      onChange={setTemperature}
                      mb="md"
                    />
                    
                    <Text size="sm" weight={500} mb={5}>
                      Max Tokens: {maxTokens}
                      {!isPremium() && maxTokens > 2000 && (
                        <Badge color="yellow" variant="light" ml="xs">
                          Limited to 2000 for standard tier
                        </Badge>
                      )}
                    </Text>
                    <Slider
                      min={100}
                      max={isPremium() ? 8000 : 2000}
                      step={100}
                      label={(value) => value}
                      value={maxTokens}
                      onChange={setMaxTokens}
                    />
                  </Box>
                )}
                
                <Textarea
                  label="Your Prompt"
                  placeholder="Enter your prompt here..."
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  minRows={4}
                  required
                  mb="md"
                />
                
                <Group position="apart">
                  <Button
                    type="button"
                    variant="outline"
                    color="gray"
                    onClick={handleClearConversation}
                  >
                    Clear
                  </Button>
                  
                  <Button
                    type="submit"
                    rightIcon={<IconSend size={16} />}
                    loading={loading}
                    disabled={!selectedModel || loading}
                  >
                    Generate
                  </Button>
                </Group>
              </Stack>
            </Paper>
            
            {tokensUsed > 0 && (
              <Paper p="xs" withBorder>
                <Group spacing="xs">
                  <Text size="sm">Tokens used:</Text>
                  <Badge>{tokensUsed}</Badge>
                </Group>
              </Paper>
            )}
          </form>
        </Grid.Col>
        
        {/* Right side - Results */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper shadow="xs" p="md" withBorder style={{ position: 'relative', minHeight: 300 }}>
            <LoadingOverlay visible={loading} overlayBlur={2} />
            
            {error ? (
              <Alert color="red" title="Error" icon={<IconInfoCircle />}>
                {error}
              </Alert>
            ) : conversationHistory.length > 0 ? (
              <ScrollArea h={500} offsetScrollbars>
                {conversationHistory.map((message, index) => (
                  <Box
                    key={index}
                    mb="md"
                    p="sm"
                    style={{
                      backgroundColor: message.role === 'user' ? '#f0f4f8' : '#fff',
                      borderRadius: 8,
                      borderLeft: `4px solid ${message.role === 'user' ? '#4f46e5' : '#10b981'}`
                    }}
                  >
                    <Group mb="xs">
                      <ThemeIcon
                        size="sm"
                        variant="light"
                        color={message.role === 'user' ? 'blue' : 'green'}
                        radius="xl"
                      >
                        {message.role === 'user' ? 'U' : 'AI'}
                      </ThemeIcon>
                      <Text weight={500} size="sm" color={message.role === 'user' ? 'blue' : 'green'}>
                        {message.role === 'user' ? 'You' : 'AI Assistant'}
                      </Text>
                    </Group>
                    <Box pl="sm">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </Box>
                  </Box>
                ))}
              </ScrollArea>
            ) : (
              <Box py={50} style={{ textAlign: 'center' }}>
                <Text color="dimmed">
                  Enter a prompt and click Generate to see AI responses here.
                </Text>
              </Box>
            )}
          </Paper>
        </Grid.Col>
      </Grid>
    </Container>
  );
};

export default Playground; 