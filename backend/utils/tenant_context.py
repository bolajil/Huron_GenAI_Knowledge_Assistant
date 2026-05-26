from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class TenantContext:
    tenant_id:       str
    dept_id:         str
    username:        str
    role:            str             = "user"
    permissions:     List[str]       = field(default_factory=list)
    namespace_scope: List[str]       = field(default_factory=list)

    def __post_init__(self):
        if not self.namespace_scope:
            self.namespace_scope = [self.dept_id]
