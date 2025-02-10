import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';

const container = document.getElementById('root');

// Check if the createRoot method is available
if (ReactDOM.createRoot) {
  // For React 18+
  const root = ReactDOM.createRoot(container);
  root.render(<App />);
} else {
  // Fallback for React versions before 18
  ReactDOM.render(<App />, container);
}
