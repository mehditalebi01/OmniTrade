import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from omnitrade.contracts import Artifact


def write_json_artifact(report_id: UUID, data: dict[str, Any], directory: Path) -> Artifact:
    directory.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, indent=2, sort_keys=True, default=str).encode()
    digest = hashlib.sha256(body).hexdigest()
    path = directory / f"{report_id}-{digest[:12]}.json"
    if not path.exists():
        path.write_bytes(body)
    return Artifact(report_id=report_id, format="json", path=str(path), sha256=digest)
