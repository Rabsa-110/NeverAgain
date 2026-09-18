# Public Deployment

This project is prepared for public deployment.

Recommended flow:

1. Push repository to GitHub.
2. Create a Web Service on Render.
3. Select Docker runtime.
4. Render uses the root Dockerfile.
5. Add environment variables:

OPENAI_API_KEY
OPENAI_MODEL
LLM_TIMEOUT_SECONDS
OPTIMIZER_TIME_LIMIT

After deployment Render provides a public HTTPS URL.

Test:

GET https://your-url/health

Expected:

{"status":"ok"}

Swagger:

https://your-url/docs
