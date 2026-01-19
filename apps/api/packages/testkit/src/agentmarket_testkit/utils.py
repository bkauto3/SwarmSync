from __future__ import annotations

import random
import string
import uuid


def random_suffix(length: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def new_uuid() -> str:
    return str(uuid.uuid4())


def unique_email(domain: str = "agents.test") -> str:
    local_part = f"user-{uuid.uuid4().hex[:8]}"
    return f"{local_part}@{domain}"


def unique_agent_name(prefix: str = "QA Agent") -> str:
    return f"{prefix} {random_suffix()}"
