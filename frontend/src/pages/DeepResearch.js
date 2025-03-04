import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container,
  Title,
  Text,
  Box,
  Button,
  Textarea,
  TextInput,
  Select,
  Group,
  Paper,
  Stack,
  Progress,
  Badge,
  Alert,
  ScrollArea,
  Tabs,
  Accordion,
  Space,
  Divider,
  Code,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useAuth } from '../context/AuthContext';
import {
  IconRobot,
  IconSend,
  IconInfoCircle,
  IconSearch,
  IconBulb,
  IconBook,
  IconRefresh,
  IconDownload,
  IconArrowRight,
  IconChartBar,
  IconArticle,
  IconCode,
  IconAlertCircle,
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';

const DeepResearch = () => {
  const { user, isPremium } = useAuth();
  
  // State
  const [researchTopic, setResearchTopic] = useState('');
  const [researchDetails, setResearchDetails] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [temperature, setTemperature] = useState(0.4);
  const [maxTokens, setMaxTokens] = useState(4000);
  const [error, setError] = useState(null);
  const [tokensUsed, setTokensUsed] = useState(0);
  const [researchId, setResearchId] = useState(() => {
    // Initialize from localStorage if available
    return localStorage.getItem('currentResearchId') || null;
  });
  const [researchStatus, setResearchStatus] = useState(null);
  const [researchFiles, setResearchFiles] = useState([]);
  const [refreshInterval, setRefreshInterval] = useState(null);
  const [modelCapabilities, setModelCapabilities] = useState({});
  const [progressUpdates, setProgressUpdates] = useState([]);
  const [researchResults, setResearchResults] = useState(null);
  const [activeTab, setActiveTab] = useState('topic');
  
  // Fetch available models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get('/models');
        setAvailableModels(response.data);
        if (response.data.length > 0) {
          setSelectedModel(response.data[0]);
        }
        
        // Fetch model capabilities
        const modelInfoResponse = await axios.get('/model-info');
        const modelInfo = {};
        modelInfoResponse.data.forEach(model => {
          modelInfo[model.id] = {
            name: model.name,
            description: model.description,
            maxTokens: model.max_tokens,
            tier: model.tier
          };
        });
        setModelCapabilities(modelInfo);
      } catch (err) {
        console.error('Error fetching models:', err);
        setError('Could not fetch available models.');
      }
    };
    
    fetchModels();
  }, []);
  
  // Effect to store researchId in localStorage when it changes
  useEffect(() => {
    if (researchId) {
      localStorage.setItem('currentResearchId', researchId);
    } else {
      localStorage.removeItem('currentResearchId');
    }
  }, [researchId]);
  
  // Effect to load research details on initial mount if researchId exists
  useEffect(() => {
    if (researchId && !researchStatus) {
      // Show loading while retrieving research status
      setLoading(true);
      
      // Show notification that we're recovering the research
      notifications.show({
        title: 'Recovering Research',
        message: 'Loading your research status...',
        color: 'blue',
        loading: true,
        autoClose: false,
        id: 'research-recovery'
      });
      
      checkResearchStatus()
        .then(status => {
          // Update notification based on research status
          notifications.update({
            id: 'research-recovery',
            title: 'Research Recovered',
            message: `Research "${status.research_id}" loaded successfully`,
            color: 'green',
            loading: false,
            autoClose: 2000
          });
        })
        .catch(() => {
          // Show error notification
          notifications.update({
            id: 'research-recovery',
            title: 'Recovery Failed',
            message: 'Could not recover research status. Try starting a new research project.',
            color: 'red',
            loading: false,
            autoClose: 5000
          });
        })
        .finally(() => setLoading(false));
    }
  }, []);
  
  // Effect to periodically check research status
  useEffect(() => {
    if (researchId && !researchStatus?.status === 'complete') {
      const interval = setInterval(checkResearchStatus, 10000);
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [researchId, researchStatus]);
  
  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!researchTopic.trim()) {
      notifications.show({
        title: 'Error',
        message: 'Please enter a research topic.',
        color: 'red'
      });
      return;
    }
    
    if (!selectedModel) {
      notifications.show({
        title: 'Error',
        message: 'Please select a model.',
        color: 'red'
      });
      return;
    }
    
    setLoading(true);
    setError(null);
    
    // Check if the model is available to the user
    const isModelPremium = modelCapabilities[selectedModel]?.tier === 'premium';
    if (isModelPremium && !isPremium()) {
      notifications.show({
        title: 'Premium Model',
        message: 'This model requires a premium account. As a test, we\'ll allow it for now.',
        color: 'yellow'
      });
    }
    
    // Calculate effective tokens based on user tier
    let effectiveTokens = maxTokens;
    if (!isPremium() && effectiveTokens > 2000) {
      effectiveTokens = 2000;
    }
    
    // Prepare research request
    const finalRequirements = `RESEARCH TOPIC: ${researchTopic}
    
ADDITIONAL DETAILS: ${researchDetails || 'No additional details provided.'}

Please conduct thorough and comprehensive research on this topic.`;
    
    try {
      // This is a placeholder for when the backend API is built
      // For now, we'll simulate a successful response
      
      const mockResearchId = 'research-' + Math.random().toString(36).substring(2, 10);
      setResearchId(mockResearchId);
      setResearchStatus({
        status: 'in_progress',
        step_info: {
          current_step: 1,
          total_steps: 6,
          description: 'Starting research phase'
        }
      });
      
      // Start checking research status
      checkResearchStatus();
      
      notifications.show({
        title: 'Research Started',
        message: 'Your deep research has been initiated. This may take several minutes.',
        color: 'blue'
      });
      
      // TODO: Replace with actual API call when backend is ready
      // const response = await axios.post('/research/start', {
      //   model: selectedModel,
      //   topic: researchTopic,
      //   details: researchDetails,
      //   max_tokens: effectiveTokens,
      //   temperature: temperature
      // });
      // setResearchId(response.data.research_id);
      
    } catch (err) {
      console.error('Error starting research:', err);
      setError(err.response?.data?.detail || 'An error occurred while starting the research.');
      
      notifications.show({
        title: 'Research Failed',
        message: err.response?.data?.detail || 'Could not start research. Please try again.',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };
  
  // Check research status
  const checkResearchStatus = async () => {
    if (!researchId) return;
    
    try {
      // This is a placeholder for when the backend API is built
      // For now, we'll simulate a status update
      
      // Simulate progressive status updates
      if (researchStatus) {
        const currentStep = researchStatus.step_info?.current_step || 1;
        const totalSteps = researchStatus.step_info?.total_steps || 6;
        
        if (currentStep < totalSteps) {
          // Simulate progress
          setResearchStatus({
            ...researchStatus,
            step_info: {
              ...researchStatus.step_info,
              current_step: currentStep + 1,
              description: `Research phase ${currentStep + 1}`
            }
          });
          
          // Simulate progress updates
          setProgressUpdates([
            ...progressUpdates,
            {
              time: new Date().toISOString(),
              message: `Completed research phase ${currentStep}`,
              files_found: currentStep * 2
            }
          ]);
          
          // Simulate complete after reaching the final step
          if (currentStep + 1 === totalSteps) {
            setTimeout(() => {
              setResearchStatus({
                ...researchStatus,
                status: 'complete',
                step_info: {
                  ...researchStatus.step_info,
                  current_step: totalSteps,
                  total_duration_minutes: 15
                }
              });
              
              // Simulate research results
              setResearchResults(`# Deep Research Findings: ${researchTopic}
              
## Executive Summary
This deep research analysis provides comprehensive insights on ${researchTopic}.

## Key Findings
1. First major insight about the topic
2. Second important discovery
3. Critical factors affecting this domain

## Detailed Analysis
The detailed analysis shows several important patterns...

## Sources and References
- Academic source 1
- Industry publication 2
- Expert interview notes
              `);
              
              notifications.show({
                title: 'Research Complete',
                message: 'Your deep research has been completed!',
                color: 'green'
              });
            }, 5000);
          }
        }
      }
      
      return researchStatus; // Return the data for promise chaining
      
      // TODO: Replace with actual API call when backend is ready
      // const response = await axios.get(`/research/status/${researchId}`);
      // setResearchStatus(response.data);
      // if (response.data.files) {
      //   setResearchFiles(response.data.files);
      // }
      // if (response.data.progress_updates) {
      //   setProgressUpdates(response.data.progress_updates);
      // }
      // if (response.data.status === 'complete') {
      //   if (refreshInterval) {
      //     clearInterval(refreshInterval);
      //     setRefreshInterval(null);
      //   }
      //   
      //   notifications.show({
      //     title: 'Research Complete',
      //     message: 'Your deep research has been completed!',
      //     color: 'green'
      //   });
      // }
      // return response.data;
    } catch (err) {
      console.error('Error checking research status:', err);
      setError('Could not retrieve research status.');
      throw err;
    }
  };
  
  // Download research findings
  const handleDownload = async () => {
    if (!researchId) return;
    
    try {
      // TODO: Replace with actual download when backend is ready
      // window.open(`/research/download/${researchId}`, '_blank');
      
      // For now, create a simple text file with the mock research results
      if (researchResults) {
        const blob = new Blob([researchResults], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `deep-research-${researchId}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Error downloading research:', err);
      notifications.show({
        title: 'Download Failed',
        message: 'Could not download the research findings. Please try again.',
        color: 'red'
      });
    }
  };
  
  // Reset state for a new research project
  const handleNewResearch = () => {
    setResearchTopic('');
    setResearchDetails('');
    setResearchId(null);
    setResearchStatus(null);
    setResearchFiles([]);
    setProgressUpdates([]);
    setResearchResults(null);
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
    localStorage.removeItem('currentResearchId');
  };
  
  // Check if this is the input form or viewing results
  const isResearching = !researchId;
  
  return (
    <Container size="xl" py="xl">
      <Title order={1} mb="md" align="center">
        <Group position="center" spacing="xs">
          <IconSearch size={36} />
          <Text>Deep Research</Text>
        </Group>
      </Title>
      
      {isResearching ? (
        <>
          <Text color="dimmed" mb="xl" align="center">
            Leverage AI to conduct comprehensive research on any topic and generate detailed findings.
          </Text>
          
          <Paper shadow="md" p="md" withBorder mb="xl">
            <Tabs value={activeTab} onTabChange={setActiveTab}>
              <Tabs.List grow mb="md">
                <Tabs.Tab value="topic" icon={<IconBulb size={16} />}>Research Topic</Tabs.Tab>
                <Tabs.Tab value="settings" icon={<IconInfoCircle size={16} />}>Advanced Settings</Tabs.Tab>
              </Tabs.List>
              
              <Tabs.Panel value="topic">
                <form onSubmit={handleSubmit}>
                  <Stack spacing="md">
                    <Box>
                      <Text weight={500} mb="xs">Research Topic</Text>
                      <Textarea
                        placeholder="Enter the main research topic or question..."
                        minRows={3}
                        value={researchTopic}
                        onChange={(e) => setResearchTopic(e.target.value)}
                        required
                      />
                    </Box>
                    
                    <Box>
                      <Text weight={500} mb="xs">Additional Details (Optional)</Text>
                      <Textarea
                        placeholder="Provide any specific aspects you want the research to focus on..."
                        minRows={5}
                        value={researchDetails}
                        onChange={(e) => setResearchDetails(e.target.value)}
                      />
                    </Box>
                    
                    <Box>
                      <Text weight={500} mb="xs">Select AI Model</Text>
                      <Select
                        data={availableModels.map(model => ({
                          value: model,
                          label: modelCapabilities[model]?.name || model,
                          description: modelCapabilities[model]?.description || '',
                          disabled: modelCapabilities[model]?.tier === 'premium' && !isPremium()
                        }))}
                        value={selectedModel}
                        onChange={setSelectedModel}
                        placeholder="Select a model"
                        required
                      />
                      
                      {selectedModel && modelCapabilities[selectedModel]?.tier === 'premium' && !isPremium() && (
                        <Alert color="yellow" mt="xs">
                          <Group>
                            <Text size="sm">This is a premium model. Normally requires a premium account.</Text>
                          </Group>
                        </Alert>
                      )}
                    </Box>
                    
                    <Group position="apart" mt="md">
                      <Button 
                        type="button" 
                        variant="subtle"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                      >
                        {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'}
                      </Button>
                      
                      <Button
                        type="submit"
                        leftIcon={<IconSearch size={16} />}
                        loading={loading}
                        disabled={!researchTopic.trim() || !selectedModel}
                      >
                        Start Deep Research
                      </Button>
                    </Group>
                    
                    {showAdvanced && (
                      <Box mt="md">
                        <Paper p="sm" withBorder>
                          <Stack spacing="md">
                            <Box>
                              <Text weight={500} mb="xs">Temperature</Text>
                              <Text size="xs" color="dimmed" mb="xs">
                                Lower values produce more focused research. Higher values introduce more creativity.
                              </Text>
                              <Group spacing="xs">
                                <Text size="sm" color="dimmed">Focused</Text>
                                <Progress
                                  value={temperature * 100}
                                  style={{ flex: 1 }}
                                  onClick={(e) => {
                                    const rect = e.currentTarget.getBoundingClientRect();
                                    const x = e.clientX - rect.left;
                                    const width = rect.width;
                                    const newTemp = Math.round((x / width) * 10) / 10;
                                    setTemperature(Math.max(0.1, Math.min(1, newTemp)));
                                  }}
                                  styles={{ bar: { cursor: 'pointer' }, root: { cursor: 'pointer' } }}
                                />
                                <Text size="sm" color="dimmed">Creative</Text>
                                <Text weight={500} ml="sm">{temperature.toFixed(1)}</Text>
                              </Group>
                            </Box>
                            
                            <Box>
                              <Text weight={500} mb="xs">Maximum Response Length</Text>
                              <Text size="xs" color="dimmed" mb="xs">
                                {isPremium() 
                                  ? 'Longer values allow for more detailed research.' 
                                  : 'Standard accounts are limited to 2,000 tokens.'}
                              </Text>
                              <TextInput
                                type="number"
                                value={maxTokens}
                                onChange={(e) => {
                                  const value = parseInt(e.target.value);
                                  if (!isNaN(value)) {
                                    const maxAllowed = isPremium() 
                                      ? (modelCapabilities[selectedModel]?.maxTokens || 8000) 
                                      : 2000;
                                    setMaxTokens(Math.min(value, maxAllowed));
                                  }
                                }}
                                min={100}
                                max={isPremium() ? (modelCapabilities[selectedModel]?.maxTokens || 8000) : 2000}
                                step={100}
                              />
                            </Box>
                          </Stack>
                        </Paper>
                      </Box>
                    )}
                    
                    {error && (
                      <Alert color="red" icon={<IconAlertCircle size={16} />} mt="md">
                        {error}
                      </Alert>
                    )}
                  </Stack>
                </form>
              </Tabs.Panel>
              
              <Tabs.Panel value="settings">
                <Paper p="md" withBorder>
                  <Stack spacing="md">
                    <Title order={3}>About Deep Research</Title>
                    <Text>
                      The Deep Research tool allows you to leverage the power of AI to conduct in-depth analysis on any topic.
                      It follows a structured research methodology that includes:
                    </Text>
                    
                    <Accordion>
                      <Accordion.Item value="methodology">
                        <Accordion.Control icon={<IconBook size={16} />}>
                          Research Methodology
                        </Accordion.Control>
                        <Accordion.Panel>
                          <Stack spacing="xs">
                            <Text>The research process follows these key steps:</Text>
                            <Box pl="md">
                              <Text>1. <b>Topic Analysis</b> - Breaking down the research question</Text>
                              <Text>2. <b>Knowledge Exploration</b> - Exploring the foundational concepts</Text>
                              <Text>3. <b>Deep Dive</b> - Analyzing patterns and connections</Text>
                              <Text>4. <b>Critical Evaluation</b> - Assessing findings and insights</Text>
                              <Text>5. <b>Synthesis</b> - Creating a comprehensive research summary</Text>
                              <Text>6. <b>Documentation</b> - Generating the final research document</Text>
                            </Box>
                          </Stack>
                        </Accordion.Panel>
                      </Accordion.Item>
                      
                      <Accordion.Item value="tips">
                        <Accordion.Control icon={<IconBulb size={16} />}>
                          Research Tips
                        </Accordion.Control>
                        <Accordion.Panel>
                          <Stack spacing="xs">
                            <Text>To get the best results from Deep Research:</Text>
                            <Box pl="md">
                              <Text>• Be specific with your research topic</Text>
                              <Text>• Use the additional details field to specify areas of focus</Text>
                              <Text>• Use a lower temperature for factual research</Text>
                              <Text>• Use a higher temperature for creative exploration</Text>
                              <Text>• Premium models generally produce more detailed research</Text>
                            </Box>
                          </Stack>
                        </Accordion.Panel>
                      </Accordion.Item>
                      
                      <Accordion.Item value="models">
                        <Accordion.Control icon={<IconRobot size={16} />}>
                          AI Models
                        </Accordion.Control>
                        <Accordion.Panel>
                          <Stack spacing="xs">
                            <Text>Different AI models have different capabilities:</Text>
                            {Object.entries(modelCapabilities).map(([id, model]) => (
                              <Paper key={id} p="xs" withBorder>
                                <Text weight={500}>{model.name || id}</Text>
                                <Text size="sm" color="dimmed">{model.description || 'No description available'}</Text>
                                <Group spacing="xs" mt="xs">
                                  <Badge color={model.tier === 'premium' ? 'violet' : 'blue'}>
                                    {model.tier === 'premium' ? 'Premium' : 'Standard'}
                                  </Badge>
                                  <Badge color="gray">Max Tokens: {model.maxTokens}</Badge>
                                </Group>
                              </Paper>
                            ))}
                          </Stack>
                        </Accordion.Panel>
                      </Accordion.Item>
                    </Accordion>
                  </Stack>
                </Paper>
              </Tabs.Panel>
            </Tabs>
          </Paper>
        </>
      ) : (
        <Stack spacing="md">
          <Paper shadow="md" p="md" withBorder>
            <Group position="apart" mb="md">
              <Title order={3}>Research Status</Title>
              <Group>
                <Button 
                  variant="light" 
                  leftIcon={<IconRefresh size={16} />}
                  onClick={checkResearchStatus}
                  disabled={loading}
                >
                  Refresh
                </Button>
                
                <Button
                  variant="outline"
                  leftIcon={<IconArrowRight size={16} />}
                  onClick={handleNewResearch}
                >
                  New Research
                </Button>
              </Group>
            </Group>
            
            {researchStatus && (
              <Box>
                <Group mb="md">
                  <Badge 
                    color={researchStatus.status === 'complete' ? 'green' : 
                          researchStatus.status === 'error' ? 'red' : 'blue'} 
                    size="lg"
                  >
                    {researchStatus.status === 'complete' ? 'Complete' : 
                    researchStatus.status === 'error' ? 'Error' : 'In Progress'}
                  </Badge>
                  
                  <Text size="sm">Research ID: {researchId}</Text>
                  
                  {researchStatus.file_count && (
                    <Badge color="indigo">
                      {researchStatus.file_count} Files Generated
                    </Badge>
                  )}
                </Group>
                
                {/* Display estimated duration for long-running tasks */}
                {researchStatus.status === 'in_progress' && researchStatus.step_info?.estimated_duration && (
                  <Alert icon={<IconInfoCircle size={16} />} color="blue" mb="md">
                    {researchStatus.step_info.estimated_duration}
                  </Alert>
                )}
                
                {/* Show duration if completed */}
                {researchStatus.status === 'complete' && researchStatus.step_info?.total_duration_minutes && (
                  <Text size="sm" mb="md">
                    Total research time: {researchStatus.step_info.total_duration_minutes} minutes
                  </Text>
                )}
                
                {/* Error message if there was an error */}
                {researchStatus.status === 'error' && researchStatus.step_info?.error && (
                  <Alert icon={<IconAlertCircle size={16} />} color="red" mb="md">
                    Error: {researchStatus.step_info.error}
                  </Alert>
                )}
                
                {/* Display progress updates in reverse chronological order */}
                {progressUpdates.length > 0 && (
                  <Box mb="md">
                    <Text weight={500} mb="xs">Progress Updates:</Text>
                    <ScrollArea h={150} mb="md">
                      <Stack spacing="xs">
                        {[...progressUpdates].reverse().map((update, index) => (
                          <Paper withBorder p="xs" key={index}>
                            <Group position="apart">
                              <Text size="sm">{update.message}</Text>
                              <Text size="xs" color="dimmed">
                                {new Date(update.time).toLocaleTimeString()}
                              </Text>
                            </Group>
                            {update.files_found && (
                              <Text size="xs" color="blue">Files: {update.files_found}</Text>
                            )}
                          </Paper>
                        ))}
                      </Stack>
                    </ScrollArea>
                  </Box>
                )}
                
                {researchStatus.status !== 'complete' && (
                  <Box mb="md">
                    <Text mb="xs">Conducting research...</Text>
                    
                    {researchStatus.step_info ? (
                      <Paper p="xs" withBorder mb="md">
                        <Text size="sm" weight={500} mb={5}>
                          {researchStatus.step_info.description || 'Processing research...'}
                        </Text>
                        
                        <Group position="apart" mb="xs">
                          <Text size="xs">Step {researchStatus.step_info.current_step} of {researchStatus.step_info.total_steps}</Text>
                        </Group>
                        
                        <Progress 
                          value={(() => {
                            // Research progress calculation
                            if (researchStatus.step_info.total_steps) {
                              // Calculate percentage based on current step
                              return (researchStatus.step_info.current_step / researchStatus.step_info.total_steps) * 100;
                            } else {
                              // Fallback
                              return Math.min(20, 20);
                            }
                          })()}
                          animate
                          size="md"
                        />
                      </Paper>
                    ) : (
                      <Progress 
                        value={20} // Conservative fallback
                        animate
                        size="md"
                      />
                    )}
                  </Box>
                )}
                
                {researchStatus.status === 'complete' && (
                  <Button
                    leftIcon={<IconDownload size={16} />}
                    onClick={handleDownload}
                    my="md"
                  >
                    Download Research Findings
                  </Button>
                )}
              </Box>
            )}
          </Paper>
          
          {/* Research Results Preview */}
          {researchStatus?.status === 'complete' && researchResults && (
            <Paper shadow="md" p="md" withBorder>
              <Title order={3} mb="md">Research Findings</Title>
              
              <Paper p="md" withBorder mb="md">
                <ScrollArea h={400}>
                  <ReactMarkdown>{researchResults}</ReactMarkdown>
                </ScrollArea>
              </Paper>
              
              <Button
                leftIcon={<IconArticle size={16} />}
                onClick={handleDownload}
                variant="light"
              >
                Download Full Report
              </Button>
            </Paper>
          )}
          
          {/* Research Files */}
          {researchFiles.length > 0 && (
            <Paper shadow="md" p="md" withBorder>
              <Title order={3} mb="md">Research Documents</Title>
              
              <Accordion>
                {researchFiles.map((file, index) => (
                  <Accordion.Item value={file} key={index}>
                    <Accordion.Control icon={<IconCode size={16} />}>
                      {file}
                    </Accordion.Control>
                    <Accordion.Panel>
                      <Code block>{`This would display the contents of ${file}`}</Code>
                    </Accordion.Panel>
                  </Accordion.Item>
                ))}
              </Accordion>
            </Paper>
          )}
        </Stack>
      )}
    </Container>
  );
};

export default DeepResearch; 