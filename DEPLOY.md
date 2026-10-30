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

## Secrets from Files

Every secret can also be read from a file instead of an environment variable, in the Docker secrets style: set `<NAME>_FILE` to the path of a file that holds the value. This keeps secret values out of the container environment.

| Variable | File variable |
| --- | --- |
| `SECRET_KEY` | `SECRET_KEY_FILE` |
| `POSTGRES_PASSWORD` | `POSTGRES_PASSWORD_FILE` |
| `FIRST_SUPERUSER_PASSWORD` | `FIRST_SUPERUSER_PASSWORD_FILE` |
| `SMTP_PASSWORD` | `SMTP_PASSWORD_FILE` |
| `SENTRY_DSN` | `SENTRY_DSN_FILE` |
| any `${VAR}` in `backends.yaml`, e.g. `GROCY_API_KEY` | `GROCY_API_KEY_FILE` |

Rules:

- `<NAME>_FILE` wins when both `<NAME>` and `<NAME>_FILE` are set.
- One trailing newline is stripped from the file content.
- A missing, unreadable or empty file stops the backend at startup with an error that names the variable and the path.
- `<NAME>_FILE` must be a real environment variable of the backend container (for example from `environment:` or `env_file:`).

Example with Compose secrets:

```yaml
services:
  backend:
    environment:
      - SECRET_KEY_FILE=/run/secrets/secret_key
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
      - FIRST_SUPERUSER_PASSWORD_FILE=/run/secrets/first_superuser_password
    secrets:
      - secret_key
      - postgres_password
      - first_superuser_password

secrets:
  secret_key:
    file: ./secrets/secret_key
  postgres_password:
    file: ./secrets/postgres_password
  first_superuser_password:
    file: ./secrets/first_superuser_password
```

The `postgres` image supports `POSTGRES_PASSWORD_FILE` as well. To keep the database password out of the environment entirely, give the `db` service the same secret and `POSTGRES_PASSWORD_FILE`, and remove `POSTGRES_PASSWORD` from `.env`: the `postgres` image refuses to start when both `POSTGRES_PASSWORD` and `POSTGRES_PASSWORD_FILE` are set.

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
2. Use environment variables or `<NAME>_FILE` secret files for secrets (see [Secrets from Files](#secrets-from-files))
3. Set up reverse proxy (nginx/traefik) for SSL
4. Configure proper CORS origins
5. Set up monitoring and backups
6. Use external database for better performance
