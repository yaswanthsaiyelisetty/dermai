# DermAI frontend

## Run locally

From `frontend/`:

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

Run the backend separately from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

The frontend uses `VITE_API_BASE_URL` (default `http://localhost:8000`). Set the backend `FRONTEND_ORIGIN` to the frontend origin when it differs from `http://localhost:5173`. The frontend stores only the opaque access token returned by the backend; it does not contain database credentials or secrets.

The backend provides validation and case association only. It does not generate a disease prediction.
