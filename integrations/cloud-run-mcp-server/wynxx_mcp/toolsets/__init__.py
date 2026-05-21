"""MCP toolsets for the Wynxx SDLC platform.

The contract is split into two toolsets, mirroring the article's tool
classification:

* ``read_only`` — observe and describe; safest to approve.
* ``advisory``  — influence decisions and draft artifacts; stricter approval.
"""

from .advisory import register_advisory
from .read_only import register_read_only

__all__ = ["register_advisory", "register_read_only"]
