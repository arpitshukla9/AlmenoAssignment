## 🚀 Setup Instructions

### Prerequisites

Install:

* Docker
* Docker Compose

No API key is required by default because the project uses a **mock LLM provider**.

---

### Step 1: Open the Project

```bash
cd path/to/transaction-pipeline
```

---

### Step 2: Create Environment Variables

```bash
cp .env.example .env
```

By default:

```env
LLM_PROVIDER=mock
```

The entire application can run end-to-end without any API key.

To use Gemini instead:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key
```

---

### Step 3: Start the Application

```bash
docker compose up --build
```

This starts four containers:

* `db` → PostgreSQL
* `redis` → Redis Queue
* `api` → FastAPI Server
* `worker` → RQ Worker

The first run may take a few minutes while Docker pulls images and installs dependencies.

The application is ready when you see:

```text
Application startup complete
```

Keep this terminal running because it streams logs from all services.

---

## 🧪 Test the Application

Open a second terminal.

### Upload the Sample CSV

```bash
cd path/to/transaction-pipeline

curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@tests/sample_transactions.csv"
```

Response:

```json
{
  "job_id": "3fa1b2c0-...",
  "status": "pending"
}
```

---

### Check Job Status

```bash
curl http://localhost:8000/jobs/<job_id>/status
```

The status transitions:

```text
pending → processing → completed
```

---

### Fetch Results

```bash
curl http://localhost:8000/jobs/<job_id>/results
```

This returns:

* Cleaned transactions
* Detected anomalies
* Category breakdown
* AI-generated narrative summary

---

## 📖 Interactive API Docs

Open:

```text
http://localhost:8000/docs
```

You can upload files and test every endpoint directly from Swagger UI.

---

## 🛑 Stop the Application

```bash
docker compose down
```

To also remove PostgreSQL volumes:

```bash
docker compose down -v
```
