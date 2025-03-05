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
  ThemeIcon,
  List,
  Progress,
  Accordion,
  Card,
  Anchor,
  Modal,
  Tabs,
  TextInput,
  Space,
  Checkbox,
  NumberInput
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useAuth } from '../context/AuthContext';
import { 
  IconRobot, 
  IconSend, 
  IconInfoCircle, 
  IconAdjustments,
  IconCode,
  IconBrandGithub,
  IconDownload,
  IconRefresh,
  IconArrowRight,
  IconWand,
  IconCheck,
  IconAlertCircle,
  IconPlayerStop,
  IconPlayerPlay
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';

const ProjectBuilder = () => {
  const { user, isPremium } = useAuth();
  
  // State
  const [projectRequirements, setProjectRequirements] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [resumeModel, setResumeModel] = useState('');  // Model to use when resuming
  const [loading, setLoading] = useState(false);
  const [refiningPrompt, setRefiningPrompt] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4000);
  const [error, setError] = useState(null);
  const [tokensUsed, setTokensUsed] = useState(0);
  const [projectId, setProjectId] = useState(() => {
    // Initialize from localStorage if available
    return localStorage.getItem('currentProjectId') || null;
  });
  const [projectStatus, setProjectStatus] = useState(null);
  const [projectFiles, setProjectFiles] = useState([]);
  const [refreshInterval, setRefreshInterval] = useState(null);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [refinedPrompt, setRefinedPrompt] = useState('');
  const [promptHistory, setPromptHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('original');
  const [modelCapabilities, setModelCapabilities] = useState({});
  const [progressUpdates, setProgressUpdates] = useState([]);

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        // Get list of available models
        const modelsResponse = await axios.get('/models');
        setAvailableModels(modelsResponse.data);
        
        // Get detailed model information
        const modelInfoResponse = await axios.get('/model-info');
        
        // Create model capabilities map
        const capabilities = {};
        modelInfoResponse.data.forEach(model => {
          capabilities[model.id] = {
            maxTokens: model.max_tokens,
            name: model.name,
            description: model.description,
            tier: model.tier
          };
        });
        
        setModelCapabilities(capabilities);
        
        // Set default model if available
        if (modelsResponse.data.length > 0 && !selectedModel) {
          setSelectedModel(modelsResponse.data[0]);
        }
      } catch (err) {
        console.error('Error fetching models:', err);
        setError('Could not fetch available models. Please try again later.');
        
        // Fallback to hardcoded capabilities if API fails
        setModelCapabilities({
          'deepseekr1': {
            maxTokens: 8192,
            name: 'DeepSeek-1 Lite',
            description: 'A capable language model for general tasks'
          },
          'claude37sonnet': {
            maxTokens: 64000,
            name: 'Claude 3.7 Sonnet',
            description: 'Anthropic\'s advanced model with strong reasoning capabilities'
          }
        });
      }
    };

    fetchModels();
  }, []); // Empty dependency array - run only once on mount

  // Add a useEffect to update maxTokens when model changes
  useEffect(() => {
    // Update max tokens when model changes based on model capabilities
    if (selectedModel && modelCapabilities[selectedModel]) {
      // For premium users, set to model's max (or lower if already set lower)
      if (isPremium()) {
        const modelMax = modelCapabilities[selectedModel].maxTokens;
        if (maxTokens > modelMax) {
          setMaxTokens(modelMax);
        }
      } else {
        // For standard users, cap at 2000
        if (maxTokens > 2000) {
          setMaxTokens(2000);
        }
      }
    }
  }, [selectedModel, modelCapabilities, isPremium]);

  // Effect to periodically check project status
  useEffect(() => {
    if (projectId && !projectStatus?.status === 'complete') {
      const interval = setInterval(checkProjectStatus, 10000);
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [projectId, projectStatus]);

  // Effect to store projectId in localStorage when it changes
  useEffect(() => {
    if (projectId) {
      localStorage.setItem('currentProjectId', projectId);
    } else {
      localStorage.removeItem('currentProjectId');
    }
  }, [projectId]);

  // Effect to load project details on initial mount if projectId exists
  useEffect(() => {
    if (projectId && !projectStatus) {
      // Show loading while retrieving project status
      setLoading(true);
      
      // Show notification that we're recovering the project
      notifications.show({
        title: 'Recovering Project',
        message: 'Loading your project status...',
        color: 'blue',
        loading: true,
        autoClose: false,
        id: 'project-recovery'
      });
      
      checkProjectStatus()
        .then(status => {
          // Update notification based on project status
          notifications.update({
            id: 'project-recovery',
            title: 'Project Recovered',
            message: `Project "${status.project_id}" loaded successfully`,
            color: 'green',
            loading: false,
            autoClose: 2000
          });
        })
        .catch(() => {
          // Show error notification
          notifications.update({
            id: 'project-recovery',
            title: 'Recovery Failed',
            message: 'Could not recover project status. Try starting a new project.',
            color: 'red',
            loading: false,
            autoClose: 5000
          });
        })
        .finally(() => setLoading(false));
    }
  }, []);

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const finalRequirements = refinedPrompt || projectRequirements;
    
    if (!finalRequirements.trim()) {
      notifications.show({
        title: 'Empty Requirements',
        message: 'Please enter project requirements before submitting.',
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
    
    // Apply token limits based on tier and model
    let effectiveTokens = maxTokens;
    if (!isPremium() && effectiveTokens > 2000) {
      effectiveTokens = 2000;
    } else if (selectedModel && modelCapabilities[selectedModel]) {
      // Ensure we don't exceed the model's maximum
      effectiveTokens = Math.min(effectiveTokens, modelCapabilities[selectedModel].maxTokens);
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/project/build', {
        model: selectedModel,
        system_prompt: 'You are an expert software developer tasked with creating a complete software project based on the user\'s requirements.',
        user_prompt: finalRequirements,
        max_tokens: effectiveTokens,
        temperature: temperature
      });
      
      setProjectId(response.data.project_id);
      setTokensUsed(response.data.tokens_used);
      setProjectDescription(response.data.response);
      
      // Start checking project status
      checkProjectStatus();
      
      notifications.show({
        title: 'Project Build Started',
        message: 'Your project is being built. This may take several minutes.',
        color: 'blue'
      });
    } catch (err) {
      console.error('Error building project:', err);
      setError(err.response?.data?.detail || 'An error occurred while building the project.');
      
      notifications.show({
        title: 'Project Build Failed',
        message: err.response?.data?.detail || 'Could not start project build. Please try again.',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle refine prompt
  const handleRefinePrompt = async () => {
    if (!projectRequirements.trim()) {
      notifications.show({
        title: 'Empty Requirements',
        message: 'Please enter project requirements to refine.',
        color: 'yellow'
      });
      return;
    }
    
    setRefiningPrompt(true);
    setError(null);
    
    try {
      const response = await axios.post('/generate', {
        model: selectedModel || availableModels[0],
        system_prompt: `You are an expert prompt engineer specializing in creating detailed project specifications for AI-based code generation. Your task is to enhance and expand on the user's project requirements to make them more detailed, specific, and comprehensive.

Please structure your response as follows:
1. Refined Project Requirements (this should be a clear, detailed project specification)
2. Technical Considerations (optional technologies to consider, architecture suggestions, etc.)
3. Potential Features (expanded list of features that would make sense for this project)

Make sure your refined prompt includes:
- Clear functional requirements
- User interface/experience descriptions
- Data models and relationships
- Expected behavior
- Any constraints or special considerations

IMPORTANT: Your response should be focused on creating a better prompt, not solving the problem directly. Do not write code.`,
        user_prompt: `Please refine and enhance the following project requirements to create a better prompt for an AI project builder:\n\n${projectRequirements}`,
        max_tokens: 2000,
        temperature: 0.7
      });
      
      // Save both original and refined prompts in history
      const newEntry = {
        original: projectRequirements,
        refined: response.data.response,
        timestamp: new Date().toISOString()
      };
      
      setPromptHistory([...promptHistory, newEntry]);
      setRefinedPrompt(response.data.response);
      setShowPromptModal(true);
      
      notifications.show({
        title: 'Prompt Refined',
        message: 'Your project requirements have been expanded and refined.',
        color: 'green'
      });
    } catch (err) {
      console.error('Error refining prompt:', err);
      setError(err.response?.data?.detail || 'An error occurred while refining the prompt.');
      
      notifications.show({
        title: 'Refinement Failed',
        message: err.response?.data?.detail || 'Could not refine your prompt. Please try again.',
        color: 'red'
      });
    } finally {
      setRefiningPrompt(false);
    }
  };

  // Accept refined prompt
  const acceptRefinedPrompt = () => {
    setProjectRequirements(refinedPrompt);
    setShowPromptModal(false);
  };

  // Check project status
  const checkProjectStatus = async () => {
    if (!projectId) return;
    
    try {
      const response = await axios.get(`/project/status/${projectId}`);
      setProjectStatus(response.data);
      
      // Update files list if available
      if (response.data.files) {
        setProjectFiles(response.data.files);
      }
      
      // Update progress information if available
      if (response.data.progress_updates) {
        setProgressUpdates(response.data.progress_updates);
      }
      
      // If project is complete or stopped, stop polling
      if (response.data.status === 'complete' || response.data.status === 'stopped' || response.data.status === 'error') {
        if (refreshInterval) {
          clearInterval(refreshInterval);
          setRefreshInterval(null);
        }
        
        if (response.data.status === 'complete') {
          notifications.show({
            title: 'Project Complete',
            message: 'Your project has been successfully built!',
            color: 'green'
          });
        } else if (response.data.status === 'stopped') {
          notifications.show({
            title: 'Project Stopped',
            message: 'The project build was stopped.',
            color: 'yellow'
          });
        }
      }
      
      return response.data; // Return the data for promise chaining
    } catch (err) {
      console.error('Error checking project status:', err);
      setError('Could not retrieve project status.');
      throw err; // Rethrow for promise handling
    }
  };

  // Stop the project build
  const handleStopBuild = async () => {
    if (!projectId) return;
    
    // Ask for confirmation
    const confirmed = window.confirm('Are you sure you want to stop the project build? This action cannot be undone.');
    if (!confirmed) return;
    
    try {
      setLoading(true);
      const response = await axios.post(`/project/stop/${projectId}`);
      
      notifications.show({
        title: 'Build Stopping',
        message: 'The project build is being stopped. This may take a moment.',
        color: 'blue'
      });
      
      // Force a status check to update the UI
      checkProjectStatus();
    } catch (err) {
      console.error('Error stopping project:', err);
      notifications.show({
        title: 'Stop Failed',
        message: err.response?.data?.detail || 'Could not stop the project build. It may have already finished.',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  // Resume a stopped project
  const handleResumeBuild = async () => {
    if (!projectId) return;
    
    try {
      setLoading(true);
      const response = await axios.post(`/project/resume/${projectId}`, {
        model: resumeModel || projectStatus.model // Use the selected resume model or fall back to original
      });
      
      notifications.show({
        title: 'Build Resuming',
        message: resumeModel 
          ? `The project build is being resumed with model: ${resumeModel}`
          : 'The project build is being resumed from where it left off.',
        color: 'blue'
      });
      
      // Force a status check to update the UI
      checkProjectStatus();
    } catch (err) {
      console.error('Error resuming project:', err);
      notifications.show({
        title: 'Resume Failed',
        message: err.response?.data?.detail || 'Could not resume the project build.',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  // Download project
  const handleDownload = async () => {
    if (!projectId) return;
    
    try {
      window.open(`/project/download/${projectId}`, '_blank');
    } catch (err) {
      console.error('Error downloading project:', err);
      notifications.show({
        title: 'Download Failed',
        message: 'Could not download the project. Please try again.',
        color: 'red'
      });
    }
  };

  // Reset state for a new project
  const handleNewProject = () => {
    setProjectRequirements('');
    setRefinedPrompt('');
    setProjectId(null);
    setProjectStatus(null);
    setProjectFiles([]);
    setProjectDescription('');
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
    localStorage.removeItem('currentProjectId');
  };

  // Check if this is the project building or viewing page
  const isBuilding = !projectId;

  return (
    <Container size="lg" py="xl">
      <Title order={1} mb="md">
        <IconCode size={30} style={{ marginRight: 10 }} />
        Project Builder
      </Title>
      
      <Text color="dimmed" mb="xl">
        Describe your project requirements and let AI build a complete software project for you.
      </Text>
      
      {/* Modal for displaying refined prompt */}
      <Modal
        opened={showPromptModal}
        onClose={() => setShowPromptModal(false)}
        title="Refined Project Requirements"
        size="xl"
      >
        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="original">Original</Tabs.Tab>
            <Tabs.Tab value="refined">Refined</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="original" pt="xs">
            <ScrollArea h={300}>
              <Text>{projectRequirements}</Text>
            </ScrollArea>
          </Tabs.Panel>

          <Tabs.Panel value="refined" pt="xs">
            <ScrollArea h={300}>
              <ReactMarkdown>{refinedPrompt}</ReactMarkdown>
            </ScrollArea>
          </Tabs.Panel>
        </Tabs>
        
        <Group position="right" mt="md">
          <Button variant="outline" onClick={() => setShowPromptModal(false)}>
            Cancel
          </Button>
          <Button 
            leftIcon={<IconCheck size={16} />}
            onClick={acceptRefinedPrompt}
          >
            Use Refined Prompt
          </Button>
        </Group>
      </Modal>
      
      {isBuilding ? (
        <Grid>
          {/* Left side - Input & Controls */}
          <Grid.Col span={{ base: 12, md: 8 }}>
            <form onSubmit={handleSubmit}>
              <Paper shadow="xs" p="md" withBorder mb="md">
                <Stack>
                  <Textarea
                    label="Project Requirements"
                    description="Describe the project you want to build in detail"
                    placeholder="I need a web application that allows users to create and manage to-do lists. The app should have user authentication, the ability to create multiple lists, add/edit/delete tasks, and mark tasks as complete."
                    value={projectRequirements}
                    onChange={(e) => setProjectRequirements(e.target.value)}
                    minRows={10}
                    required
                    mb="md"
                  />
                  
                  <Group position="right" mb="md">
                    <Button
                      leftIcon={<IconWand size={16} />}
                      variant="light"
                      color="violet"
                      onClick={handleRefinePrompt}
                      loading={refiningPrompt}
                      disabled={!projectRequirements.trim()}
                    >
                      Refine Prompt with AI
                    </Button>
                  </Group>
                  
                  {refinedPrompt && (
                    <Alert color="green" title="Using Refined Requirements" icon={<IconWand size={16} />}>
                      <Group>
                        <Text size="sm">Your requirements have been refined for better results</Text>
                        <Button 
                          variant="subtle" 
                          size="xs" 
                          onClick={() => setShowPromptModal(true)}>
                          View Refined
                        </Button>
                      </Group>
                    </Alert>
                  )}
                  
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
                        {!isPremium() && (
                          <Badge color="yellow" variant="light" ml="xs">
                            Limited to 2000 for standard tier
                          </Badge>
                        )}
                        {isPremium() && selectedModel && modelCapabilities[selectedModel] && (
                          <Badge color="blue" variant="light" ml="xs">
                            Premium tier: up to {modelCapabilities[selectedModel].maxTokens}
                          </Badge>
                        )}
                      </Text>
                      <Text size="xs" color="dimmed" mb={8}>
                        {selectedModel && modelCapabilities[selectedModel] ? 
                          `Model maximum: ${modelCapabilities[selectedModel].maxTokens} tokens` : 
                          'Select a model to see maximum tokens'}
                      </Text>
                      <Slider
                        min={1000}
                        max={
                          isPremium() 
                            ? (selectedModel && modelCapabilities[selectedModel]?.maxTokens 
                                ? modelCapabilities[selectedModel].maxTokens 
                                : 8192)
                            : 2000
                        }
                        step={500}
                        label={(value) => value}
                        value={maxTokens}
                        onChange={setMaxTokens}
                      />
                    </Box>
                  )}
                  
                  <Group position="right">
                    <Button
                      type="submit"
                      rightIcon={<IconSend size={16} />}
                      loading={loading}
                      disabled={!selectedModel || loading || (!projectRequirements.trim() && !refinedPrompt.trim())}
                    >
                      Build Project
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            </form>
          </Grid.Col>
          
          {/* Right side - Information */}
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Paper shadow="xs" p="md" withBorder mb="md">
              <Title order={3} mb="md">How It Works</Title>
              <List spacing="sm">
                <List.Item>Describe your project requirements in detail</List.Item>
                <List.Item>Refine your requirements with AI assistance (optional)</List.Item>
                <List.Item>AI analyzes your requirements and plans the project</List.Item>
                <List.Item>Complete project structure is generated</List.Item>
                <List.Item>All necessary files are created with implementation</List.Item>
                <List.Item>Download the complete project as a zip file</List.Item>
              </List>
              
              <Text mt="md" size="sm" color="dimmed">
                The more detailed your requirements, the better the resulting project.
              </Text>
            </Paper>
            
            {promptHistory.length > 0 && (
              <Paper shadow="xs" p="md" withBorder mt="md">
                <Title order={3} mb="md">Prompt History</Title>
                <Accordion>
                  {promptHistory.map((entry, index) => (
                    <Accordion.Item key={index} value={`prompt-${index}`}>
                      <Accordion.Control>
                        <Group>
                          <Text>Refinement #{index + 1}</Text>
                          <Badge size="sm">
                            {new Date(entry.timestamp).toLocaleTimeString()}
                          </Badge>
                        </Group>
                      </Accordion.Control>
                      <Accordion.Panel>
                        <Tabs defaultValue="original">
                          <Tabs.List>
                            <Tabs.Tab value="original">Original</Tabs.Tab>
                            <Tabs.Tab value="refined">Refined</Tabs.Tab>
                          </Tabs.List>
                          <Tabs.Panel value="original" pt="xs">
                            <Text size="sm">{entry.original.substring(0, 200)}...</Text>
                          </Tabs.Panel>
                          <Tabs.Panel value="refined" pt="xs">
                            <Text size="sm">{entry.refined.substring(0, 200)}...</Text>
                            <Button 
                              variant="subtle" 
                              size="xs" 
                              mt="xs"
                              onClick={() => {
                                setRefinedPrompt(entry.refined);
                                notifications.show({
                                  title: 'Prompt Selected',
                                  message: 'This refined prompt is now selected for use',
                                  color: 'blue'
                                });
                              }}
                            >
                              Use This Prompt
                            </Button>
                          </Tabs.Panel>
                        </Tabs>
                      </Accordion.Panel>
                    </Accordion.Item>
                  ))}
                </Accordion>
              </Paper>
            )}
          </Grid.Col>
        </Grid>
      ) : (
        <Grid>
          {/* Project Status */}
          <Grid.Col span={12}>
            <Paper shadow="xs" p="md" withBorder mb="md">
              <Group position="apart" mb="md">
                <Title order={3}>Project Status</Title>
                <Group>
                  <Button 
                    variant="light" 
                    leftIcon={<IconRefresh size={16} />}
                    onClick={checkProjectStatus}
                    disabled={loading}
                  >
                    Refresh
                  </Button>
                  
                  {projectStatus && projectStatus.status === 'in_progress' && (
                    <Button 
                      variant="filled" 
                      color="red"
                      leftIcon={<IconPlayerStop size={16} />}
                      onClick={handleStopBuild}
                      disabled={loading}
                    >
                      Stop Build
                    </Button>
                  )}
                  
                  <Button
                    variant="outline"
                    leftIcon={<IconArrowRight size={16} />}
                    onClick={handleNewProject}
                  >
                    New Project
                  </Button>
                </Group>
              </Group>
              
              {projectStatus && (
                <Box>
                  <Group mb="md">
                    <Badge 
                      color={projectStatus.status === 'complete' ? 'green' : 
                            projectStatus.status === 'error' ? 'red' : 
                            projectStatus.status === 'stopped' ? 'yellow' : 'blue'} 
                      size="lg"
                    >
                      {projectStatus.status === 'complete' ? 'Complete' : 
                       projectStatus.status === 'error' ? 'Error' : 
                       projectStatus.status === 'stopped' ? 'Stopped' : 'In Progress'}
                    </Badge>
                    
                    <Text size="sm">Project ID: {projectId}</Text>
                    
                    {projectStatus.file_count && (
                      <Badge color="indigo">
                        {projectStatus.file_count} Files Generated
                      </Badge>
                    )}
                  </Group>
                  
                  {/* Display estimated duration for long-running tasks */}
                  {projectStatus.status === 'in_progress' && projectStatus.step_info?.estimated_duration && (
                    <Alert icon={<IconInfoCircle size={16} />} color="blue" mb="md">
                      {projectStatus.step_info.estimated_duration}
                    </Alert>
                  )}
                  
                  {/* Show duration if completed */}
                  {projectStatus.status === 'complete' && projectStatus.step_info?.total_duration_minutes && (
                    <Text size="sm" mb="md">
                      Total build time: {projectStatus.step_info.total_duration_minutes} minutes
                    </Text>
                  )}
                  
                  {/* Show model switching UI when project is stopped */}
                  {projectStatus.status === 'stopped' && (
                    <Paper p="xs" withBorder mb="md">
                      <Title order={5} mb="xs">Resume with Different Model</Title>
                      <Text size="sm" mb="md" color="dimmed">
                        If you encountered issues with the current model ({projectStatus.model || "unknown"}), 
                        you can try a different one.
                      </Text>
                      <Group position="apart" align="flex-end">
                        <Select
                          label="Select Model"
                          placeholder={projectStatus.model || "Choose a model"}
                          data={availableModels.map(model => typeof model === 'string' ? 
                            { value: model, label: model } : 
                            { value: model.id || model.toString(), label: model.name || model.toString() }
                          )}
                          value={resumeModel}
                          onChange={setResumeModel}
                          style={{ minWidth: 200 }}
                        />
                        <Button 
                          variant="filled" 
                          color="green"
                          leftIcon={<IconPlayerPlay size={16} />}
                          onClick={handleResumeBuild}
                          disabled={loading}
                        >
                          Resume Build
                        </Button>
                      </Group>
                    </Paper>
                  )}
                  
                  {/* Error message if there was an error */}
                  {projectStatus.status === 'error' && projectStatus.step_info?.error && (
                    <Alert icon={<IconAlertCircle size={16} />} color="red" mb="md">
                      Error: {projectStatus.step_info.error}
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
                  
                  {projectStatus.status !== 'complete' && (
                    <Box mb="md">
                      <Text mb="xs">Building your project...</Text>
                      
                      {projectStatus.step_info ? (
                        <Paper p="xs" withBorder mb="md">
                          <Text size="sm" weight={500} mb={5}>
                            {projectStatus.step_info.description || 'Processing project...'}
                          </Text>
                          
                          <Group position="apart" mb="xs">
                            <Text size="xs">Step {projectStatus.step_info.current_step} of {projectStatus.step_info.total_steps}</Text>
                          </Group>
                          
                          <Progress 
                            value={(() => {
                              // More accurate progress calculation
                              if (projectStatus.step_info.total_steps) {
                                // Extract step information
                                const currentStep = projectStatus.step_info.current_step;
                                const totalSteps = projectStatus.step_info.total_steps;
                                
                                // Weight the progress - planning phases are only 30% of total progress
                                // Implementation phases are the remaining 70%
                                if (currentStep <= 3) { // Planning phases (steps 1-3)
                                  return (currentStep / 3) * 30; // First 30% of progress bar
                                } else { // Implementation phases (steps 4+)
                                  const implementationProgress = (currentStep - 3) / (totalSteps - 3);
                                  return 30 + (implementationProgress * 70); // Remaining 70% of progress
                                }
                              } else {
                                // Fallback - very conservative estimate
                                return Math.min((projectFiles.length / 20) * 30, 30); // Max 30% for just files
                              }
                            })()}
                            animate
                            size="md"
                          />
                        </Paper>
                      ) : (
                        <Progress 
                          value={Math.min((projectFiles.length / 20) * 30, 30)} // More conservative fallback
                          animate
                          size="md"
                        />
                      )}
                    </Box>
                  )}
                  
                  {projectStatus.status === 'complete' && (
                    <Button
                      leftIcon={<IconDownload size={16} />}
                      onClick={handleDownload}
                      my="md"
                    >
                      Download Project
                    </Button>
                  )}
                </Box>
              )}
            </Paper>
          </Grid.Col>
          
          {/* Project Files */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Paper shadow="xs" p="md" withBorder mb="md">
              <Title order={3} mb="md">Project Files</Title>
              
              {projectFiles.length > 0 ? (
                <Accordion>
                  {projectFiles
                    .filter(file => !file.includes('__pycache__') && !file.includes('status.json'))
                    .sort()
                    .map((file, index) => (
                      <Accordion.Item value={file} key={index}>
                        <Accordion.Control>
                          <Group>
                            <Text>{file}</Text>
                            {file.endsWith('.py') && <Badge color="blue">Python</Badge>}
                            {file.endsWith('.js') && <Badge color="yellow">JavaScript</Badge>}
                            {file.endsWith('.html') && <Badge color="orange">HTML</Badge>}
                            {file.endsWith('.css') && <Badge color="green">CSS</Badge>}
                            {file.includes('README') && <Badge color="gray">Docs</Badge>}
                            {file.includes('SUMMARY') && <Badge color="violet">Summary</Badge>}
                          </Group>
                        </Accordion.Control>
                        <Accordion.Panel>
                          <Text size="sm" color="dimmed">
                            File path: {file}
                          </Text>
                          <Button
                            variant="subtle"
                            size="xs"
                            mt="xs"
                            disabled={!projectStatus?.status === 'complete'}
                          >
                            View Code
                          </Button>
                        </Accordion.Panel>
                      </Accordion.Item>
                    ))}
                </Accordion>
              ) : (
                <Text color="dimmed">No files generated yet.</Text>
              )}
            </Paper>
          </Grid.Col>
          
          {/* Project Description */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Paper shadow="xs" p="md" withBorder mb="md">
              <Title order={3} mb="md">Project Requirements</Title>
              <ScrollArea h={300} offsetScrollbars>
                {refinedPrompt ? (
                  <ReactMarkdown>{refinedPrompt}</ReactMarkdown>
                ) : (
                  <Text>{projectRequirements}</Text>
                )}
              </ScrollArea>
            </Paper>
            
            {projectStatus?.status === 'complete' && (
              <Card shadow="xs" p="md" withBorder mt="md">
                <Group position="apart" mb="md">
                  <Title order={3}>What's Next?</Title>
                  <Badge color="green">Ready to Use</Badge>
                </Group>
                
                <List>
                  <List.Item>Download your complete project</List.Item>
                  <List.Item>Extract the ZIP file to your computer</List.Item>
                  <List.Item>Follow the README.md file for setup instructions</List.Item>
                  <List.Item>
                    <Group spacing="xs">
                      <Text>Upload to GitHub</Text>
                      <Anchor href="https://github.com/new" target="_blank">
                        <IconBrandGithub size={16} />
                      </Anchor>
                    </Group>
                  </List.Item>
                </List>
              </Card>
            )}
          </Grid.Col>
        </Grid>
      )}
    </Container>
  );
};

export default ProjectBuilder; 