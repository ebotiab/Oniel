# Oniel · visor

React + TypeScript estricto + Vite + MapLibre GL. Instrucciones completas en el [README raíz](../README.md).

```bash
npm install
npm run dev        # http://localhost:5173, proxy /api → ONIEL_API_PROXY (por defecto http://127.0.0.1:8000)
npm run typecheck
npm run build
npx playwright test
```

`public/data/` contiene la instantánea estática que exporta `oniel-data export snapshot`; el visor arranca siempre con ella y pasa a la API (`VITE_API_URL`) en cuanto `/healthz` responde, de modo que el despertar del servidor en Render no retrasa el mapa. Sin API, se queda en la instantánea.
