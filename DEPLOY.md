# Deployment with Docker Compose

This guide shows how to deploy the Product Matcher application using pre-built Docker images from GitHub Container Registry. No building required!

## Quick Start

1. **Download the compose file:**
   ```bash
   curl -o docker-compose.yml https://raw.githubusercontent.com/miguelangel-nubla/product-matcher/master/docker-compose.yml
   ```

2. **Start the application:**
   ```bash
   docker compose up -d
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
   - Adminer (Database UI): http://localhost:8080

## Default Credentials

- **Admin User:** admin@example.com
- **Admin Password:** changethis
- **Database:** postgres/changethis

## Environment Variables (Optional)

Create a `.env` file to customize settings:

```env
# Database
POSTGRES_PASSWORD=your_secure_password
POSTGRES_USER=postgres
POSTGRES_DB=app

# Admin User
FIRST_SUPERUSER=your@email.com
FIRST_SUPERUSER_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_secret_key_here

# Frontend URL (if different)
FRONTEND_HOST=http://localhost:3000
VITE_API_URL=http://localhost:8000

# Email (optional)
SMTP_HOST=your_smtp_host
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
EMAILS_FROM_EMAIL=noreply@yourdomain.com
```

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
- **5432:** PostgreSQL (exposed for external access)

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

For production deployment:

1. Change all default passwords
2. Use environment variables for secrets
3. Set up reverse proxy (nginx/traefik) for SSL
4. Configure proper CORS origins
5. Set up monitoring and backups
6. Use external database for better performance
