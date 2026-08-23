from typing import Optional

from pydantic import BaseModel


class ProductEntitlementResponse(BaseModel):
    product_key: str
    name: str
    enabled: bool
    launch_url: Optional[str] = None  # only meaningful when enabled=True