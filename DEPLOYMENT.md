# 🚀 Deployment Guide

Complete guide for deploying the Hospital Bulk Processor API to production.

## Table of Contents

- [Render Deployment (Docker)](#render-deployment-docker)
- [Render Deployment (Native)](#render-deployment-native)
- [Other Platforms](#other-platforms)
- [Environment Variables](#environment-variables)
- [Post-Deployment](#post-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

## Render Deployment (Docker)

### Prerequisites

- GitHub/GitLab account
- Render account (free tier available at [render.com](https://render.com))
- Project pushed to a Git repository

### Step-by-Step Guide

#### 1. Prepare Your Repository

Ensure these files are in your repository:
- `Dockerfile`
- `requirements.txt`
- `app/` directory with all application files
- `.env.example` (environment template)

**Important**: Do NOT commit `.env` file with secrets!

#### 2. Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up or log in
3. Connect your GitHub/GitLab account

#### 3. Create New Web Service

1. Click **"New +"** → **"Web Service"**
2. Connect your repository
3. Configure the service:

**Basic Settings:**
```
Name:                hospital-bulk-processor
Region:              Choose closest to your users (e.g., Oregon, Frankfurt)
Branch:              main (or your default branch)
Runtime:             Docker
```

**Docker Settings:**
```
Dockerfile Path:     ./Dockerfile
Docker Context:      . (root directory)
Docker Command:      (leave empty - uses CMD from Dockerfile)
```

**Instance Type:**
```
Free Tier:           Free (512 MB RAM, shared CPU)
Starter:             $7/month (512 MB RAM, shared CPU)
Standard:            $25/month (2 GB RAM, dedicated CPU) - Recommended
```

#### 4. Configure Environment Variables

Add these in Render's Environment section:

| Variable | Value | Required |
|----------|-------|----------|
| `HOSPITAL_API_BASE_URL` | `https://hospital-directory.onrender.com` | Yes |
| `MAX_CSV_ROWS` | `20` | Yes |
| `UPLOAD_MAX_SIZE_MB` | `5` | Yes |
| `PORT` | `8000` | No (Render sets this) |
| `HOST` | `0.0.0.0` | Yes |

**Note**: Render automatically provides `PORT` variable. Your app should use it.

#### 5. Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repository
   - Build the Docker image
   - Deploy the container
   - Provide a URL like `https://hospital-bulk-processor.onrender.com`

#### 6. Verify Deployment

Once deployed, test your endpoints:

```bash
# Health check
curl https://your-app.onrender.com/health

# API documentation
https://your-app.onrender.com/docs

# Test upload
curl -X POST "https://your-app.onrender.com/hospitals/bulk" \
  -F "file=@sample_hospitals.csv"
```

### Auto-Deploy on Push

Render automatically redeploys when you push to your connected branch:

```bash
git add .
git commit -m "Update application"
git push origin main
```

Render will automatically build and deploy the new version.

## Render Deployment (Native)

If you prefer not to use Docker:

#### Build Command:
```bash
pip install -r requirements.txt
```

#### Start Command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### Environment:
```
Python Version:      3.10.x
```

**Note**: Docker deployment is recommended for consistency and reliability.

## Other Platforms

### Docker Hub + Any Cloud Platform

#### 1. Build and Push to Docker Hub

```bash
# Build the image
docker build -t yourusername/hospital-bulk-processor:latest .

# Login to Docker Hub
docker login

# Push the image
docker push yourusername/hospital-bulk-processor:latest
```

#### 2. Deploy to Cloud Platform

Use the image `yourusername/hospital-bulk-processor:latest` on any platform:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform
- Heroku Container Registry

### AWS Elastic Container Service (ECS)

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name hospital-bulk-processor

# 2. Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 3. Build and tag
docker build -t hospital-bulk-processor .
docker tag hospital-bulk-processor:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hospital-bulk-processor:latest

# 4. Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hospital-bulk-processor:latest

# 5. Create ECS task definition and service using AWS Console or CLI
```

### Google Cloud Run

```bash
# 1. Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/hospital-bulk-processor

# 2. Deploy to Cloud Run
gcloud run deploy hospital-bulk-processor \
  --image gcr.io/PROJECT_ID/hospital-bulk-processor \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars HOSPITAL_API_BASE_URL=https://hospital-directory.onrender.com
```

### DigitalOcean App Platform

1. Go to DigitalOcean → Apps
2. Create New App → Select repository
3. Choose "Dockerfile" as build method
4. Configure environment variables
5. Deploy

### Heroku (Container)

```bash
# 1. Login to Heroku
heroku login
heroku container:login

# 2. Create app
heroku create hospital-bulk-processor

# 3. Build and push
heroku container:push web -a hospital-bulk-processor

# 4. Release
heroku container:release web -a hospital-bulk-processor

# 5. Set environment variables
heroku config:set HOSPITAL_API_BASE_URL=https://hospital-directory.onrender.com -a hospital-bulk-processor
```

## Environment Variables

### Required Variables

```bash
HOSPITAL_API_BASE_URL=https://hospital-directory.onrender.com
MAX_CSV_ROWS=20
UPLOAD_MAX_SIZE_MB=5
HOST=0.0.0.0
```

### Optional Variables

```bash
PORT=8000                    # Usually set by platform
LOG_LEVEL=info              # info, debug, warning, error
ENVIRONMENT=production      # production, staging, development
```

### Setting Environment Variables

**Render:**
- Dashboard → Service → Environment
- Add each variable manually

**Docker Compose:**
```yaml
environment:
  - VARIABLE_NAME=value
```

**Docker Run:**
```bash
docker run -e VARIABLE_NAME=value ...
```

**Heroku:**
```bash
heroku config:set VARIABLE_NAME=value
```

**AWS ECS:**
- Task Definition → Environment Variables

## Post-Deployment

### 1. Test All Endpoints

```bash
BASE_URL="https://your-app.onrender.com"

# Health check
curl $BASE_URL/health

# Root endpoint
curl $BASE_URL/

# API documentation
open $BASE_URL/docs
```

### 2. Test CSV Upload

```bash
curl -X POST "$BASE_URL/hospitals/bulk" \
  -H "accept: application/json" \
  -F "file=@sample_hospitals.csv"
```

### 3. Monitor Initial Performance

- Check response times
- Verify batch activation works
- Test with various CSV sizes
- Monitor error rates

### 4. Set Up Custom Domain (Optional)

**Render:**
1. Go to Settings → Custom Domains
2. Add your domain (e.g., api.yourdomain.com)
3. Configure DNS records as instructed
4. SSL certificate is auto-provisioned

## Monitoring & Maintenance

### Logging

**Render Logs:**
```bash
# Via dashboard: Service → Logs
# Real-time logs stream automatically
```

**Docker Logs:**
```bash
# If self-hosting
docker-compose logs -f
```

### Health Monitoring

Set up monitoring services:

**Uptime Robot** (Free):
- Monitor endpoint: `https://your-app.onrender.com/health`
- Check interval: 5 minutes
- Alert on downtime

**Better Uptime**:
- More advanced monitoring
- Status pages
- Incident management

**Custom Health Check Script:**
```bash
#!/bin/bash
# check_health.sh

URL="https://your-app.onrender.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✓ Service is healthy"
    exit 0
else
    echo "✗ Service is down (HTTP $RESPONSE)"
    exit 1
fi
```

### Performance Monitoring

**Application Performance:**
- Response times
- Request rates
- Error rates
- Batch processing times

**Resource Usage:**
- CPU usage
- Memory usage
- Network I/O

**Render Metrics:**
- Available in Render dashboard
- Shows CPU, memory, request count

### Alerts

Set up alerts for:
- Service downtime (>5 minutes)
- High error rate (>5%)
- High response time (>5 seconds)
- Memory usage (>80%)
- Failed batch activations

## Scaling

### Horizontal Scaling (Multiple Instances)

**Render:**
- Upgrade to Standard plan or higher
- Increase instance count in settings
- Load balancing is automatic

**Docker Compose:**
```bash
docker-compose up -d --scale app=3
```

### Vertical Scaling (Bigger Instance)

**Render:**
- Upgrade instance type
- More RAM and CPU
- Zero downtime upgrade

### Performance Optimization

1. **Concurrent Processing**: Already implemented with `asyncio.gather()`
2. **Connection Pooling**: Consider adding for HTTP client
3. **Caching**: Add Redis for batch status caching
4. **CDN**: Use CloudFlare for static assets (if any)

## Troubleshooting

### Common Issues

#### Service Won't Start

**Check:**
```bash
# Render logs
# Look for:
- Missing environment variables
- Port binding errors
- Python import errors
```

**Solution:**
- Verify all required env vars are set
- Check Dockerfile CMD is correct
- Ensure dependencies are installed

#### External API Connection Failed

**Check:**
```bash
# Test from deployment
curl https://hospital-directory.onrender.com/docs
```

**Solution:**
- Verify API URL in environment variables
- Check if external API is up
- Verify network connectivity

#### Out of Memory

**Symptoms:**
- Container crashes
- 502/503 errors
- Slow responses

**Solution:**
- Upgrade instance size
- Optimize batch processing
- Add memory limits in Docker

#### Slow Performance

**Check:**
- Concurrent requests count
- External API response time
- Instance CPU/memory usage

**Solution:**
- Scale horizontally (more instances)
- Optimize CSV processing
- Add request queuing

### Debug Mode

Enable debug logging:

```bash
# Add environment variable
LOG_LEVEL=debug
```

Or modify code temporarily:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Rollback

If deployment fails:

**Render:**
1. Go to Service → Deploys
2. Find previous successful deploy
3. Click "Redeploy"

**Docker:**
```bash
# Use previous image tag
docker pull yourusername/hospital-bulk-processor:previous-tag
docker-compose up -d
```

## Security Best Practices

1. **Never commit secrets** to repository
2. **Use environment variables** for all configuration
3. **Enable HTTPS** (automatic on Render)
4. **Validate all inputs** (already implemented)
5. **Keep dependencies updated**
6. **Monitor for vulnerabilities**
7. **Use non-root user in Docker** (already configured)
8. **Set resource limits** in production
9. **Enable CORS carefully** (adjust for production)
10. **Add rate limiting** for production use

## Backup & Recovery

### Backup Strategy

Since this service is stateless (no database), backup focuses on:
- Application code (in Git)
- Configuration (documented)
- Deployment settings (documented)

### Disaster Recovery

**If service goes down:**
1. Check Render status page
2. Review recent deploys
3. Rollback if needed
4. Deploy to backup region

**If data corruption:**
- No persistent data in this service
- All data managed by external Hospital API
- Recovery handled by external API

## CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python test_setup.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Render
        # Render auto-deploys on push
        run: echo "Deployed to Render automatically"
```

## Cost Estimation

### Render Pricing

| Tier | Price | RAM | CPU | Use Case |
|------|-------|-----|-----|----------|
| Free | $0 | 512 MB | Shared | Testing, demos |
| Starter | $7/mo | 512 MB | Shared | Small projects |
| Standard | $25/mo | 2 GB | Dedicated | Production (recommended) |
| Pro | $85/mo | 4 GB | Dedicated | High traffic |

**Free Tier Limitations:**
- Spins down after 15 min inactivity
- Slower cold starts
- Limited to 750 hours/month

**Recommendation**: Start with Free for testing, upgrade to Standard for production.

## Support

### Getting Help

1. **Documentation**: Check this guide and README.md
2. **Logs**: Review application logs for errors
3. **Render Support**: docs.render.com
4. **API Documentation**: `/docs` endpoint
5. **External API**: hospital-directory.onrender.com/docs

### Useful Links

- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Hospital Directory API](https://hospital-directory.onrender.com/docs)

---

**Last Updated**: December 2024
**Version**: 1.0.0

For questions or issues, refer to the main [README.md](README.md) or [DOCKER.md](DOCKER.md) documentation.