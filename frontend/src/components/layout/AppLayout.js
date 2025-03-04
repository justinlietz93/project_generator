import React from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import {
  AppShell,
  Text,
  Box,
  Group,
  ThemeIcon,
  UnstyledButton,
  Divider,
  useMantineTheme,
  Menu,
  Avatar,
  Button,
  Burger,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconDashboard,
  IconWand,
  IconCreditCard,
  IconLogin,
  IconUserPlus,
  IconUser,
  IconLogout,
  IconBrain,
  IconCode,
} from '@tabler/icons-react';
import { useAuth } from '../../context/AuthContext';

const MainLinks = ({ closeNav }) => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  const links = [
    { icon: IconDashboard, color: 'blue', label: 'Dashboard', path: '/' },
    { icon: IconWand, color: 'violet', label: 'AI Playground', path: '/playground' },
    { icon: IconCode, color: 'green', label: 'Project Builder', path: '/project-builder' },
    { icon: IconCreditCard, color: 'pink', label: 'Subscription', path: '/pricing' },
  ];

  const authLinks = [
    { icon: IconLogin, color: 'green', label: 'Login', path: '/login' },
    { icon: IconUserPlus, color: 'orange', label: 'Register', path: '/register' },
  ];

  const displayLinks = isAuthenticated ? links : [...links, ...authLinks];

  return (
    <Box>
      {displayLinks.map((link) => (
        <UnstyledButton
          key={link.label}
          component={Link}
          to={link.path}
          onClick={() => closeNav && closeNav()}
          sx={(theme) => ({
            display: 'block',
            width: '100%',
            padding: theme.spacing.xs,
            borderRadius: theme.radius.sm,
            color: theme.colorScheme === 'dark' ? theme.colors.dark[0] : theme.black,
            backgroundColor: 
              location.pathname === link.path 
                ? theme.colorScheme === 'dark' 
                  ? theme.colors[link.color][9] + '40'
                  : theme.colors[link.color][0]
                : 'transparent',
            '&:hover': {
              backgroundColor:
                theme.colorScheme === 'dark'
                  ? theme.colors[link.color][9] + '40'
                  : theme.colors[link.color][0],
            },
          })}
        >
          <Group>
            <ThemeIcon color={link.color} variant="light">
              {React.createElement(link.icon, { size: 16 })}
            </ThemeIcon>
            <Text size="sm">{link.label}</Text>
          </Group>
        </UnstyledButton>
      ))}
    </Box>
  );
};

const AppLayout = () => {
  const theme = useMantineTheme();
  const [opened, { toggle }] = useDisclosure(false);
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <AppShell
      padding="md"
      header={{ height: 60 }}
      navbar={{
        width: 280,
        breakpoint: 'sm',
        collapsed: { mobile: !opened }
      }}
    >
      <AppShell.Header p="md">
        <Group justify="space-between" style={{ height: '100%' }}>
          <Box style={{ display: 'flex', alignItems: 'center' }}>
            <Burger
              opened={opened}
              onClick={toggle}
              size="sm"
              color={theme.colors.gray[6]}
              hiddenFrom="sm"
              mr="md"
            />
            <Text
              component={Link}
              to="/"
              size="lg"
              fw={700}
              variant="gradient" 
              gradient={{ from: 'violet', to: 'grape', deg: 135 }}
              style={{
                textDecoration: 'none',
              }}
            >
              Scry AI Project Builder
            </Text>
          </Box>

          <Group>
            {isAuthenticated ? (
              <Menu position="bottom-end" shadow="md">
                <Menu.Target>
                  <UnstyledButton>
                    <Group spacing="xs">
                      <Avatar 
                        radius="xl" 
                        size={32} 
                        color="violet"
                        variant="gradient" 
                        gradient={{ from: 'violet', to: 'grape', deg: 135 }}
                      >
                        {user?.username?.charAt(0).toUpperCase() || 'U'}
                      </Avatar>
                      <Box visibleFrom="sm">
                        <Text size="sm" fw={500}>
                          {user?.username || 'User'}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {user?.tier === 'premium' ? 'Premium' : 'Standard'}
                        </Text>
                      </Box>
                    </Group>
                  </UnstyledButton>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>Account</Menu.Label>
                  <Menu.Item leftSection={<IconUser size={14} />} component={Link} to="/profile">
                    Profile
                  </Menu.Item>
                  <Menu.Item leftSection={<IconCreditCard size={14} />} component={Link} to="/pricing">
                    Subscription
                  </Menu.Item>
                  <Menu.Divider />
                  <Menu.Item 
                    color="red" 
                    leftSection={<IconLogout size={14} />}
                    onClick={handleLogout}
                  >
                    Logout
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            ) : (
              <Box visibleFrom="sm">
                <Group>
                  <Button 
                    variant="outline" 
                    size="xs"
                    component={Link}
                    to="/login"
                  >
                    Login
                  </Button>
                  <Button 
                    size="xs"
                    gradient={{ from: 'violet', to: 'grape', deg: 135 }}
                    variant="gradient"
                    component={Link}
                    to="/register"
                  >
                    Register
                  </Button>
                </Group>
              </Box>
            )}
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <AppShell.Section mb="xl">
          <Group justify="center">
            <ThemeIcon size="xl" radius="md" variant="gradient" gradient={{ from: 'violet', to: 'grape', deg: 135 }}>
              {React.createElement(IconBrain, { size: 24 })}
            </ThemeIcon>
            <Text size="lg" fw={700} variant="gradient" gradient={{ from: 'violet', to: 'grape', deg: 135 }}>
              SCRY AI
            </Text>
          </Group>
        </AppShell.Section>
        
        <AppShell.Section grow>
          <MainLinks closeNav={() => opened && toggle()} />
        </AppShell.Section>
        
        {isAuthenticated && (
          <AppShell.Section>
            <Divider my="sm" />
            <UnstyledButton
              onClick={handleLogout}
              sx={(theme) => ({
                display: 'block',
                width: '100%',
                padding: theme.spacing.xs,
                borderRadius: theme.radius.sm,
                color: theme.colors.red[6],
                '&:hover': {
                  backgroundColor:
                    theme.colorScheme === 'dark'
                      ? theme.colors.red[9] + '40'
                      : theme.colors.red[0],
                },
              })}
            >
              <Group>
                <ThemeIcon color="red" variant="light">
                  {React.createElement(IconLogout, { size: 16 })}
                </ThemeIcon>
                <Text size="sm">Logout</Text>
              </Group>
            </UnstyledButton>
          </AppShell.Section>
        )}
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
};

export default AppLayout; 