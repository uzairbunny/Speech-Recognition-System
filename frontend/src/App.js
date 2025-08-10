import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, AppBar, Toolbar, Typography } from '@mui/material';

// Pages
import LiveTranscription from './pages/LiveTranscription';
import SessionHistory from './pages/SessionHistory';
import SpeakerManagement from './pages/SpeakerManagement';
import Dashboard from './pages/Dashboard';

// Components
import Navigation from './components/Navigation';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex' }}>
          <AppBar
            position="fixed"
            sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
          >
            <Toolbar>
              <Typography variant="h6" noWrap component="div">
                Speech Recognition System
              </Typography>
            </Toolbar>
          </AppBar>
          
          <Navigation />
          
          <Box
            component="main"
            sx={{
              flexGrow: 1,
              bgcolor: 'background.default',
              p: 3,
              mt: 8, // AppBar height
            }}
          >
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live" element={<LiveTranscription />} />
              <Route path="/sessions" element={<SessionHistory />} />
              <Route path="/speakers" element={<SpeakerManagement />} />
            </Routes>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
