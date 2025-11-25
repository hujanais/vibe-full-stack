### Setup Postgres database

docker run --name rocket-vibe-db -d -p 54321:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres123 postgres:latest
