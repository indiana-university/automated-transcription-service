import React from 'react';
import ReactDOM from 'react-dom/client';
// Configures Amplify as an import side effect; keep this before App.
import './amplify-config';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
