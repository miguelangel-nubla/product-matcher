# Deployment with Docker Compose

This guide shows how to deploy the Product Matcher application using pre-built Docker images from GitHub Container Registry. No building required!

## Quick Start

1. **Download the compose file:**
   ```bash
   curl -o docker-compose.yml https://raw.githubusercontent.com/miguelangel-nubla/product-matcher/master/docker-compose.yml
   ```

2. **Create a `.env` file and replace every `changethis` secret** (`SECRET_KEY`, `POSTGRES_PASSWORD`, `FIRST_SUPERUSER_PASSWORD`). The Compose file sets `ENVIRONMENT=production`, and the backend will not start until those values change.

3. **Start the application:**
   ```bash
   docker compose up -d
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs

## Default Credentials

Replace these before starting the published Compose file. Production mode refuses `changethis`.

- **Admin User:** admin@example.com
- **Admin Password:** changethis
- **Database:** postgres/changethis

## Environment Variables (Optional)

Modify the `.env` file to customize settings:

## Generate Secure Keys

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Stopping the Application

```bash
docker compose down
```

## Updating to Latest Version

```bash
docker compose pull
docker compose up -d
```

## Volumes

The database data is persisted in a Docker volume `app-db-data`. To completely reset:

```bash
docker compose down -v
```

## Ports

- **3000:** Frontend (React)
- **8000:** Backend API (FastAPI)

PostgreSQL stays on the Compose network. The test overlay publishes port 5432 when you need it from the host.

## Troubleshooting

1. **Check container status:**
   ```bash
   docker compose ps
   ```

2. **View logs:**
   ```bash
   docker compose logs backend
   docker compose logs frontend
   ```

3. **Health checks:**
   - Backend: http://localhost:8000/api/v1/utils/health-check/
   - Frontend: http://localhost:3000

## Production Considerations

The published Compose file sets `ENVIRONMENT=production`. The backend refuses to start while `SECRET_KEY`, `POSTGRES_PASSWORD`, or `FIRST_SUPERUSER_PASSWORD` is still `changethis`.

For production deployment:

1. Change all default passwords before the first start
2. Use environment variables for secrets
3. Set up reverse proxy (nginx/traefik) for SSL
4. Configure proper CORS origins
5. Set up monitoring and backups
6. Use external database for better performance
