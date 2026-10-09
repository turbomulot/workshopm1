# Mission SENTINEL-X

Workshop EPSI Bac+4 2026-27.

- `frontend/` : dashboard (React + Vite)
- `backend/` : API capteurs, MQTT → PostgreSQL (Node.js)
- `webcam-detection/` : détection YOLO et badges QR (Python)
- `firmware/` : ESP8266 (PlatformIO)
- `security/` : PKI, Mosquitto, durcissement

## Lancer

```bash
cd backend && cp .env.example .env && docker compose up -d --build
cd frontend && cp .env.example .env && npm install && npm run dev
cd webcam-detection && pip install -r requirements.txt && python stream_detection.py
```
