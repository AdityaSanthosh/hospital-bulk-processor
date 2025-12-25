# Hospital Bulk Processor API

A FastAPI-based bulk processing system that integrates with the Hospital Directory API to handle CSV uploads and process hospital records concurrently.

## 🚀 Features

- **Bulk CSV Upload**: Upload CSV files with up to 20 hospital records
- **Concurrent Processing**: Process multiple hospitals simultaneously for optimal performance
- **Batch Management**: Automatic batch creation and activation
- **Error Handling**: Comprehensive validation and error reporting
- **Rollback Support**: Automatic cleanup on failure
- **Interactive API Documentation**: Swagger UI and ReDoc

## 📋 Requirements

### Option 1: Docker (Recommended)
- Docker 20.10+
- Docker Compose 1.29+

### Option 2: Local Python
- Python 3.8+
- pip (Python package manager)

## 🛠️ Installation

### Option 1: Docker (Recommended)

Docker provides the easiest way to run the application with all dependencies included.

1. **Navigate to the project directory:**
   ```bash
   cd hospital-bulk-processor
   ```

2. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

   Or use the provided script:
   ```bash
   ./docker-build.sh
   docker-compose up
   ```

3. **Run in background (detached mode):**
   ```bash
   docker-compose up -d
   ```

4. **Using Make commands (optional):**
   ```bash
   make build    # Build the Docker image
   make up       # Start in production mode
   make dev      # Start in development mode (hot reload)
   make logs     # View logs
   make down     # Stop containers
   make shell    # Open shell in container
   ```

### Option 2: Local Python Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd hospital-bulk-processor
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables (optional):**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` to customize settings if needed.

## 🚦 Running the Application

### With Docker (Recommended)

**Production mode:**
```bash
docker-compose up
```

**Development mode with hot reload:**
```bash
docker-compose -f docker-compose.dev.yml up
```

**Background mode:**
```bash
docker-compose up -d
```

**Using Make:**
```bash
make up       # Production mode
make dev      # Development mode
make up-d     # Background mode
```

**Stop the application:**
```bash
docker-compose down
# or
make down
```

### With Local Python

**Development Mode:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using Python:

```bash
python -m app.main
```

Or using the start script:

```bash
./start.sh
```

The API will be available at: `http://localhost:8000`

### API Documentation

Once the server is running, access the interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📝 API Endpoints

### Root Endpoint
```
GET /
```
Returns API information and available endpoints.

### Health Check
```
GET /health
```
Returns the health status of the service.

### Bulk Create Hospitals
```
POST /hospitals/bulk
```

Upload a CSV file to create multiple hospitals in bulk.

**Request:**
- Content-Type: `multipart/form-data`
- Body: CSV file with hospital data

**CSV Format:**
```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Medical Center,456 Oak Ave,555-5678
Community Health Clinic,789 Pine Rd,
```

**Required Columns:**
- `name`: Hospital name (required)
- `address`: Hospital address (required)
- `phone`: Hospital phone number (optional)

**Constraints:**
- Maximum 20 hospitals per CSV
- Maximum file size: 5MB
- File must be UTF-8 encoded

**Response Example:**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_hospitals": 3,
  "processed_hospitals": 3,
  "failed_hospitals": 0,
  "processing_time_seconds": 2.45,
  "batch_activated": true,
  "hospitals": [
    {
      "row": 2,
      "hospital_id": 101,
      "name": "General Hospital",
      "status": "created_and_activated",
      "error_message": null
    },
    {
      "row": 3,
      "hospital_id": 102,
      "name": "City Medical Center",
      "status": "created_and_activated",
      "error_message": null
    },
    {
      "row": 4,
      "hospital_id": 103,
      "name": "Community Health Clinic",
      "status": "created_and_activated",
      "error_message": null
    }
  ]
}
```

## 🧪 Testing with cURL

### Upload a CSV file:

```bash
curl -X POST "http://localhost:8000/hospitals/bulk" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@hospitals.csv"
```

### Check health status:

```bash
curl -X GET "http://localhost:8000/health"
```

## 🧪 Testing with Python

```python
import requests

# Upload CSV file
with open('hospitals.csv', 'rb') as f:
    files = {'file': ('hospitals.csv', f, 'text/csv')}
    response = requests.post('http://localhost:8000/hospitals/bulk', files=files)
    print(response.json())
```

## 📁 Project Structure

```
hospital-bulk-processor/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application and endpoints
│   ├── models.py            # Pydantic models for request/response
│   ├── services.py          # Business logic and API client
│   └── utils.py             # CSV validation and utilities
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker Compose configuration (production)
├── docker-compose.dev.yml   # Docker Compose configuration (development)
├── .dockerignore           # Docker ignore rules
├── Makefile                # Make commands for Docker
├── docker-build.sh         # Docker build script
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment variables
├── .gitignore              # Git ignore rules
├── start.sh                # Local start script
├── test_setup.py           # Setup verification script
├── sample_hospitals.csv    # Sample CSV for testing
└── README.md               # This file
```

## ⚙️ Configuration

Configuration is managed through environment variables. See `.env.example` for available options:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOSPITAL_API_BASE_URL` | `https://hospital-directory.onrender.com` | Base URL of the Hospital Directory API |
| `MAX_CSV_ROWS` | `20` | Maximum number of rows allowed in CSV |
| `UPLOAD_MAX_SIZE_MB` | `5` | Maximum file size in MB |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

## 🔄 How It Works

1. **CSV Upload**: User uploads a CSV file via the `/hospitals/bulk` endpoint
2. **Validation**: System validates CSV format, headers, and content
3. **Batch Creation**: A unique batch UUID is generated
4. **Concurrent Processing**: All hospitals are created concurrently via the Hospital Directory API
5. **Batch Activation**: If all hospitals are created successfully, the batch is activated
6. **Rollback**: If any hospital fails or activation fails, the entire batch is deleted
7. **Response**: Detailed results are returned including processing time and individual hospital statuses

## 🛡️ Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid CSV format, missing required fields, or validation errors
- **500 Internal Server Error**: Unexpected errors during processing

All errors include detailed messages to help diagnose issues.

## 🐳 Docker Commands Reference

### Basic Commands

```bash
# Build the image
docker-compose build

# Start containers
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Restart containers
docker-compose restart

# Open shell in container
docker-compose exec app /bin/bash

# Run tests in container
docker-compose exec app python test_setup.py
```

### Using Make (Easier)

```bash
make build          # Build Docker image
make up             # Start in production mode
make up-d           # Start in background
make dev            # Start in development mode (hot reload)
make down           # Stop containers
make restart        # Restart containers
make logs           # View logs
make shell          # Open shell in container
make test           # Run tests
make clean          # Clean up Docker resources
make health         # Check service health
make test-upload    # Test with sample CSV
```

## 🚀 Deployment

### Deploy with Docker to Render

1. Create a new Web Service on [Render](https://render.com)
2. Connect your GitHub repository
3. Configure the service:
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Command**: (leave empty, uses CMD from Dockerfile)
4. Add environment variables in Render dashboard:
   - `HOSPITAL_API_BASE_URL=https://hospital-directory.onrender.com`
   - `MAX_CSV_ROWS=20`
   - `PORT=8000` (Render provides this)
5. Deploy!

### Deploy without Docker to Render

1. Create a new Web Service on [Render](https://render.com)
2. Connect your GitHub repository
3. Configure the service:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in Render dashboard
5. Deploy!

## 📊 Performance

- **Concurrent Processing**: Hospitals are processed concurrently using `asyncio.gather()` for optimal performance
- **Expected Processing Time**: ~2-5 seconds for 20 hospitals (depends on external API response time)
- **Async HTTP Client**: Uses `httpx` for efficient async HTTP operations

## 🔐 Security Considerations

- File size limits prevent DoS attacks
- CSV validation prevents malicious input
- UTF-8 encoding requirement prevents encoding attacks
- CORS configured (adjust for production)

## 📄 License

This project is provided as-is for the Hospital Bulk Processing System task.

## 🤝 Contributing

This is a task-specific project. For improvements or bug fixes, please discuss with the project maintainer.

## 🐛 Troubleshooting

### Docker Issues

**Port already in use:**
```bash
# Stop other services on port 8000 or change the port in docker-compose.yml
docker-compose down
```

**Permission denied:**
```bash
# Make scripts executable
chmod +x docker-build.sh start.sh
```

**Container fails to start:**
```bash
# Check logs
docker-compose logs

# Rebuild from scratch
make rebuild
```

**Cannot connect to external API:**
```bash
# Check if the API is accessible
curl https://hospital-directory.onrender.com/docs

# Check container network
docker-compose exec app ping hospital-directory.onrender.com
```

## 📞 Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review error messages in the response
3. Check server logs:
   - Docker: `docker-compose logs -f` or `make logs`
   - Local: Check terminal output
4. Verify external API is accessible

---

**Note**: This system integrates with the Hospital Directory API at `https://hospital-directory.onrender.com`. Ensure the external API is accessible for the system to function properly.