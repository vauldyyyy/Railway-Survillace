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

import React, { Component, ErrorInfo } from 'react';

class ErrorBoundary extends Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: 'red', padding: '20px', fontFamily: 'monospace', backgroundColor: '#05080F', width: '100%', height: '100vh' }}>
          <h2>React Crashed!</h2>
          <pre style={{whiteSpace: 'pre-wrap'}}>{this.state.error?.toString()}</pre>
          <pre style={{whiteSpace: 'pre-wrap'}}>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
