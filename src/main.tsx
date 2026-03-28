import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { startMetricsSimulation, startBridgePoller } from './store/useSystemStore';
import useSystemStore from './store/useSystemStore';

// Start backend pollers (run outside React tree so they survive re-renders)
startMetricsSimulation();
startBridgePoller();

// Kick off WebSocket connection
useSystemStore.getState().connectWebSocket();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
