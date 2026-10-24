# aws-ecs-helloworld

A production-ready **Hello World container for Amazon ECS**. Deploy it to verify your cluster, service, load balancer and health checks end to end, before shipping your real application.

![aws-ecs-helloworld home page](https://raw.githubusercontent.com/code4mk/aws-ecs-helloworld/main/docs/screenshot.png)

## Features

- **FastAPI + uvicorn** with a clean, plain HTML home page (no JavaScript, strict CSP)
- **Health checks built in**: `/health` (liveness) and `/ready` (readiness)
- **Curl-free container health check**: `python -m app.healthcheck`
- **ECS-aware**: detects Amazon ECS and exposes live task metadata (cluster, service, task, AZ, private IP, image) at `/api/info`
- **CloudWatch-friendly JSON logs** with request IDs; health check requests are not logged by default
- **Secure by default**: runs as a non-root user (UID 10001), security headers, works with a read-only root filesystem
- **Graceful shutdown** on `SIGTERM`, so ECS deployments drain cleanly

## Quick start

```bash
docker run --rm -p 8080:8080 hiremostafa/aws-ecs-helloworld:latest
```

Open http://localhost:8080

## Endpoints

| Path        | Description                                            |
| ----------- | ------------------------------------------------------ |
| `/`         | HTML home page                                         |
| `/health`   | Liveness check. Use for ALB and container health       |
| `/ready`    | Readiness check. Returns `503` during startup/shutdown |
| `/api/info` | App, runtime and ECS task metadata as JSON             |
| `/docs`     | OpenAPI documentation                                  |

## Deploy on Amazon ECS

- **Image:** `hiremostafa/aws-ecs-helloworld:1.0.0`
- **Container port:** `8080`
- **ALB target group:** protocol `HTTP`, port `8080`, target type `ip`, health check path `/health`
- **Container health check** (task definition):

```json
"healthCheck": {
  "command": ["CMD", "python", "-m", "app.healthcheck"],
  "interval": 30,
  "timeout": 5,
  "retries": 3,
  "startPeriod": 10
}
```

The container listens on **8080** because it runs as a non-root user.

## Configuration

| Variable                    | Default                       | Description                          |
| --------------------------- | ----------------------------- | ------------------------------------ |
| `PORT`                      | `8080`                        | HTTP port                            |
| `MESSAGE`                   | `Your Amazon ECS app is live` | Headline on the home page            |
| `APP_NAME`                  | `aws-ecs-helloworld`          | Application name                     |
| `LOG_LEVEL`                 | `info`                        | `debug`, `info`, `warning`, `error`  |
| `LOG_HEALTH_CHECKS`         | `false`                       | Log `/health` and `/ready` requests  |
| `ECS_METADATA_TIMEOUT`      | `2`                           | ECS metadata request timeout (s)     |
| `GRACEFUL_SHUTDOWN_TIMEOUT` | `20`                          | Seconds to finish in-flight requests |

## Tags

| Tag      | Platform      |
| -------- | ------------- |
| `latest` | `linux/amd64` |
| `1.0.0`  | `linux/amd64` |

## Source

GitHub: https://github.com/code4mk/aws-ecs-helloworld

## Author

Crafted with ♥ by [code4mk](https://github.com/code4mk). Questions, ideas or work inquiries: **hiremostafa@gmail.com**

> Sample application. Not affiliated with or endorsed by Amazon Web Services.
