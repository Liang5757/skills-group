import { hydrateRoot } from 'react-dom/client';
import { App } from './App.tsx';
import type { MarketPage } from '../types/page.ts';

const root = document.getElementById('app');
const serialized = document.getElementById('market-data')?.textContent;
if (!root || !serialized) throw new Error('The generated market page is missing its bootstrap data');
// This JSON is embedded by the same build that renders the page.
const data = JSON.parse(serialized) as MarketPage;
hydrateRoot(root, <App {...data} />);
