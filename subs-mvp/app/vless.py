from base64 import b64encode
from uuid import UUID

from .config import settings


def build_vless(uid: UUID, fmt: str = "plain") -> str:
    domain = settings.SUBS_DOMAIN
    port = settings.XRAY_PORT
    flow = settings.XRAY_FLOW
    link = (
        f"vless://{uid}@{domain}:{port}?type=tcp&security=tls&flow={flow}"
        f"&sni={domain}&fp=chrome#{domain}-vision"
    )
    if fmt == "b64":
        return b64encode(link.encode()).decode()
    return link
