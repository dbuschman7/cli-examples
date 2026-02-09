# Redpanda Connect HTML Server

A lightweight Redpanda Connect server running in Alpine Linux, configured in streams mode with HTML endpoints and basic authentication.

## Features

- 🐳 Alpine-based Docker container (small footprint)
- 🔄 Streams mode with dynamic stream loading
- 🔐 Basic authentication (username: `admin`, password: `admin`)
- 🌐 HTML status pages and REST endpoints
- 📁 Auto-reloading streams from the `/streams` directory

## Quick Start

### Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down
```

### Access the Server

Once running, access the server at `http://localhost:4195`

**Note:** For this initial version, basic authentication is not configured. To add authentication, you can configure it using environment variables or by modifying the stream configurations.

## Available Endpoints

- **[/status](http://localhost:4195/status)** - HTML status page with auto-refresh
- **[/health](http://localhost:4195/health)** - JSON health check endpoint
- **[/echo](http://localhost:4195/echo)** - Echo service (POST requests)

## Project Structure

```
connect-html-server/
├── Dockerfile              # Alpine-based container definition
├── docker-compose.yml      # Docker Compose configuration
├── config.yaml            # Main Redpanda Connect configuration
├── streams/               # Stream definitions (auto-loaded)
│   ├── echo.yaml         # Echo service stream
│   ├── health.yaml       # Health check stream
│   └── status.yaml       # Status page stream
└── README.md             # This file
```

## Adding New Streams

To add a new stream, simply create a new `.yaml` file in the `streams/` directory. The server will automatically detect and load it within 5 seconds (configured by `auto_reload_interval`).

### Example Stream Template

```yaml
# streams/my-stream.yaml

input:
  generate:
    interval: 1s
    mapping: |
      root.message = "Hello, World!"
      root.timestamp = now()

output:
  http_server:
    path: /my-endpoint
    stream_path: /my-endpoint
```

After creating the file, the new endpoint will be available at `http://localhost:4195/my-endpoint`

## Configuration

### Basic Authentication

Edit [config.yaml](config.yaml) to change authentication settings:

```yaml
http:
  basic_auth:
    enabled: true
    realm: "Redpanda Connect"
    username: admin
    password: admin
```

### Stream Auto-Reload

Streams are automatically reloaded from the `/streams` directory:

```yaml
stream:
  auto_reload_dir: /streams
  auto_reload_interval: 5s
```

### Port Configuration

Change the port in [docker-compose.yml](docker-compose.yml):

```yaml
ports:
  - "4195:4195"  # Change the first port number
```

## Testing

### Test with curl

```bash
# Health check (JSON)
curl -u admin:admin http://localhost:4195/health

# Status page (HTML)
curl -u admin:admin http://localhost:4195/status

# Echo service (POST)
curl -u admin:admin -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}' \
  http://localhost:4195/echo
```

### Test in Browser

1. Open http://localhost:4195/status in your browser
2. Enter username: `admin` and password: `admin`
3. View the auto-refreshing status page

## Troubleshooting

### View container logs
```bash
docker-compose logs -f
```

### Check if container is running
```bash
docker-compose ps
```

### Restart the server
```bash
docker-compose restart
```

### Rebuild after changes
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Security Notes

⚠️ **Important:** This example uses hardcoded credentials (`admin`/`admin`) for demonstration purposes only. 

For production use:
- Use environment variables for credentials
- Implement proper secrets management
- Use HTTPS/TLS encryption
- Consider using OAuth2 or JWT tokens
- Restrict network access appropriately

## Resources

- [Redpanda Connect Documentation](https://docs.redpanda.com/redpanda-connect/)
- [Streams Mode Documentation](https://docs.redpanda.com/redpanda-connect/guides/streams_mode/about/)
- [Bloblang Language Guide](https://docs.redpanda.com/redpanda-connect/guides/bloblang/about/)

## License

This is an example project for demonstration purposes.
