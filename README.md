# aws-ecs-helloworld

A production-quality Hello World container for **Amazon ECS**, the ECS counterpart of
`mcr.microsoft.com/azuredocs/containerapps-helloworld`. Deploy it to verify a cluster, service,
load balancer and health checks end to end.

- FastAPI + uvicorn, plain HTML home page (no JavaScript, strict CSP)
- Detects ECS and exposes live task metadata (cluster, service, task, AZ, private IP, image) at `/api/info`
- `/health` (liveness) and `/ready` (readiness) endpoints, plus a curl-free container health check
- Structured JSON logs for CloudWatch, request IDs, security headers
- Non-root, slim, multi-arch image (`linux/amd64`, `linux/arm64` for Graviton)

## Run locally

```bash
docker build -t aws-ecs-helloworld .
docker run --rm -p 8080:8080 aws-ecs-helloworld
open http://localhost:8080
```

## Endpoints

| Path        | Purpose                                                      |
| ----------- | ------------------------------------------------------------ |
| `/`         | HTML home page                                               |
| `/health`   | Liveness. Use for the ALB target group and container health check |
| `/ready`    | Readiness. Returns `503` during startup and shutdown          |
| `/api/info` | App, runtime and ECS metadata as JSON                         |
| `/docs`     | OpenAPI UI                                                    |

## Configuration

| Variable                    | Default                       |
| --------------------------- | ----------------------------- |
| `PORT`                      | `8080`                        |
| `MESSAGE`                   | `Your Amazon ECS app is live` |
| `APP_NAME`                  | `aws-ecs-helloworld`          |
| `LOG_LEVEL`                 | `info`                        |
| `LOG_HEALTH_CHECKS`         | `false`                       |
| `ECS_METADATA_TIMEOUT`      | `2` (seconds)                 |
| `GRACEFUL_SHUTDOWN_TIMEOUT` | `20` (seconds)                |

`APP_VERSION`, `BUILD_SHA` and `BUILD_DATE` are set at build time with `--build-arg`.

## Deploy to ECS

1. Push the image to ECR or GHCR (the included GitHub Actions workflow publishes multi-arch images to GHCR).
2. Create a task definition with container port `8080` and, optionally, this container health check:
   `["CMD", "python", "-m", "app.healthcheck"]`.
3. Create a service behind an ALB with target group: protocol `HTTP`, port `8080`,
   target type `ip`, health check path `/health`.

The container listens on **8080** because it runs as a non-root user.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
.venv/bin/python -m app
```

## Author

Crafted with ♥ by [code4mk](https://github.com/code4mk). Questions, ideas or work inquiries: [hiremostafa@gmail.com](mailto:hiremostafa@gmail.com)
