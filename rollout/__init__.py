"""
Department Rollout Package

Automates namespace provisioning and rollout across all departments.
"""

from rollout.department_rollout import (
    DepartmentRollout,
    DepartmentRolloutResult,
    RolloutStatus,
    RolloutStep,
    DEPARTMENT_SAMPLE_DOCS,
    DEPARTMENT_TEST_QUERIES,
)

__all__ = [
    "DepartmentRollout",
    "DepartmentRolloutResult",
    "RolloutStatus",
    "RolloutStep",
    "DEPARTMENT_SAMPLE_DOCS",
    "DEPARTMENT_TEST_QUERIES",
]
