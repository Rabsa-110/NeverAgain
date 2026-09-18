# GridWise API

## Run locally

Create environment:

python -m venv venv

Activate:

Windows:
venv\Scripts\activate

Install:

pip install -r requirements.txt

Run:

uvicorn app.main:app --reload

Open:

http://127.0.0.1:8000/docs

## Test

pytest

## Docker

docker build -t gridwise-api .

docker run -p 8000:8000 gridwise-api
