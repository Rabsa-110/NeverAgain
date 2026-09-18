# GridWise Deployment

This deployment package is prepared for a public HTTP API deployment.

## Public deployment

The service must be deployed on a cloud platform. After deployment the platform provides a public URL like:

https://your-service-url.example.com

The judge can then call:

GET /health
POST /optimize-energy

## Docker local verification

Build from project root:

```bash
docker build -f deployment/Dockerfile -t gridwise-api .
```

Run:

```bash
docker run -p 8000:8000 gridwise-api
```

Test:

```
http://localhost:8000/health
```

## Render deployment

1. Push this repository to GitHub.
2. Create a new Web Service on Render.
3. Select Docker runtime.
4. Use deployment/render.yaml settings.
5. After deployment, use the generated public URL as the submission endpoint.

No API keys or secrets should be committed.
