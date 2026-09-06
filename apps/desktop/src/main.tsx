import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import { MotionProvider } from '@alice/ui';
import App from './app/App';
import { WebAccessGate } from './app/WebAccessGate';
import './styles/tokens.css';
import './styles/global.css';
import './styles/shell.css';
import './styles/workspace.css';
class ErrorBoundary extends React.Component<React.PropsWithChildren, { error: string }> {
  state = { error: '' };
  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }
  render() {
    return this.state.error ? (
      <main className="fatal">
        <h1>ALICE console unavailable</h1>
        <p>{this.state.error}</p>
        <button onClick={() => location.reload()}>Reload console</button>
      </main>
    ) : (
      this.props.children
    );
  }
}
ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <MotionProvider>
      <WebAccessGate>
        <App />
      </WebAccessGate>
    </MotionProvider>
  </ErrorBoundary>,
);
