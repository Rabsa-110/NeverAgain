# GridWise Deployment

Deployment configuration for the GridWise API.

## Build

From project root:

docker build -f deployment/Dockerfile -t gridwise-api .

## Run

docker run -p 8000:8000 gridwise-api

Test:

http://localhost:8000/health

## Docker Compose

docker compose -f deployment/docker-compose.yml up --build
