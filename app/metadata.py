import asyncio
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

METADATA_ENV = "ECS_CONTAINER_METADATA_URI_V4"


@dataclass(frozen=True)
class EcsMetadata:
    cluster: str | None = None
    service_name: str | None = None
    task_arn: str | None = None
    task_id: str | None = None
    task_definition: str | None = None
    launch_type: str | None = None
    availability_zone: str | None = None
    region: str | None = None
    container_name: str | None = None
    image: str | None = None
    private_ip: str | None = None
    task_cpu: str | None = None
    task_memory: str | None = None
    started_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _short_name(arn_or_name: str | None) -> str | None:
    if not arn_or_name:
        return None
    return arn_or_name.rsplit("/", 1)[-1]


def _region_from_arn(arn: str | None) -> str | None:
    parts = (arn or "").split(":")
    return parts[3] if len(parts) > 3 and parts[3] else None


def parse_metadata(container: dict[str, Any], task: dict[str, Any]) -> EcsMetadata:
    task_arn = task.get("TaskARN")
    family, revision = task.get("Family"), task.get("Revision")
    networks = container.get("Networks") or [{}]
    ipv4 = networks[0].get("IPv4Addresses") or []
    limits = task.get("Limits") or {}

    return EcsMetadata(
        cluster=_short_name(task.get("Cluster")),
        service_name=task.get("ServiceName"),
        task_arn=task_arn,
        task_id=_short_name(task_arn),
        task_definition=f"{family}:{revision}" if family and revision else family,
        launch_type=task.get("LaunchType"),
        availability_zone=task.get("AvailabilityZone"),
        region=os.getenv("AWS_REGION") or _region_from_arn(task_arn),
        container_name=container.get("Name"),
        image=container.get("Image"),
        private_ip=ipv4[0] if ipv4 else None,
        task_cpu=f"{limits['CPU']} vCPU" if "CPU" in limits else None,
        task_memory=f"{limits['Memory']} MiB" if "Memory" in limits else None,
        started_at=container.get("StartedAt"),
    )


async def fetch_ecs_metadata(timeout: float) -> EcsMetadata | None:
    """Returns None when not running on ECS or when the endpoint is unreachable."""
    base_url = os.getenv(METADATA_ENV)
    if not base_url:
        logger.info("ECS metadata endpoint not set; running outside Amazon ECS")
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            container_resp, task_resp = await asyncio.gather(
                client.get(base_url), client.get(f"{base_url}/task")
            )
            container_resp.raise_for_status()
            task_resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch ECS task metadata", extra={"error": str(exc)})
        return None

    metadata = parse_metadata(container_resp.json(), task_resp.json())
    logger.info("Loaded ECS task metadata", extra={"ecs": metadata.to_dict()})
    return metadata
