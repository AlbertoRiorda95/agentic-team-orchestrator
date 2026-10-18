import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { StatusPage } from './status-page';
import './index.css';

const root = document.getElementById('root');
if (!root) throw new Error('Missing #root element');

createRoot(root).render(
  <StrictMode>
    <StatusPage />
  </StrictMode>,
);
