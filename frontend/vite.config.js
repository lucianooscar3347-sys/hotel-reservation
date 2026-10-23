import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Sécurité de session : aucune page ni donnée ne doit pouvoir être relue depuis le cache du navigateur (bouton « Retour »).
const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0', Pragma: 'no-cache', Expires: '0' };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, headers: noStore },
  preview: { headers: noStore },
  build: {
    rollupOptions: {
      // Sépare les grosses bibliothèques : meilleur cache navigateur, chargement initial plus léger.
      output: { manualChunks: { react: ['react', 'react-dom', 'react-router-dom'], charts: ['recharts'], http: ['axios', 'react-toastify'] } },
    },
  },
});
