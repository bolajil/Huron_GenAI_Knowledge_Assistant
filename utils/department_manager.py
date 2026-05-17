"""
Dynamic Department Manager

Allows runtime creation and management of departments with:
- Namespace provisioning
- Configuration persistence
- Attention profile assignment
- Web crawler URL configuration

Usage:
    from utils.department_manager import DepartmentManager
    
    manager = DepartmentManager()
    
    # Add new department
    manager.create_department(
        dept_id="compliance",
        display_name="Compliance & Risk",
        sensitivity="confidential",
        seed_urls=["https://compliance.huron.com"]
    )
    
    # List departments
    departments = manager.list_departments()
"""

import os
import logging
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Default registry path
DEFAULT_REGISTRY_PATH = Path("config/dept_namespace_registry.yml")


class SensitivityLevel(Enum):
    """Department sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    HIPAA_PHI = "hipaa_phi"


@dataclass
class AttentionProfile:
    """Department attention profile for RAG retrieval"""
    retrieval_weight: float = 1.0
    rerank_boost: float = 1.0
    context_window: int = 4096
    max_chunks: int = 10
    prefer_recent: bool = False
    cross_dept_allowed: bool = False
    

@dataclass
class WebCrawlerConfig:
    """Web crawler configuration for a department"""
    enabled: bool = False
    seed_urls: List[str] = field(default_factory=list)
    max_pages: int = 50
    max_depth: int = 2
    schedule: str = "weekly"  # daily, weekly, monthly
    ttl_days: int = 90


@dataclass
class Department:
    """Department configuration"""
    dept_id: str
    display_name: str
    namespace: str
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL
    description: str = ""
    
    # Document types supported
    document_types: List[str] = field(default_factory=lambda: ["general"])
    
    # Pinecone configuration
    dedicated_nodes: bool = False
    pod_type: str = "p1.x1"
    
    # Profiles
    attention_profile: AttentionProfile = field(default_factory=AttentionProfile)
    web_crawler: WebCrawlerConfig = field(default_factory=WebCrawlerConfig)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = "system"
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        return {
            "display_name": self.display_name,
            "namespace": self.namespace,
            "sensitivity": self.sensitivity.value,
            "description": self.description,
            "document_types": self.document_types,
            "dedicated_nodes": self.dedicated_nodes,
            "pod_type": self.pod_type,
            "attention_profile": asdict(self.attention_profile),
            "web_crawler": asdict(self.web_crawler),
            "created_at": self.created_at,
            "created_by": self.created_by,
            "active": self.active,
        }
    
    @classmethod
    def from_dict(cls, dept_id: str, data: Dict[str, Any]) -> "Department":
        """Create Department from dictionary"""
        attention_data = data.get("attention_profile", {})
        crawler_data = data.get("web_crawler", {})
        
        # Filter attention_data to only known fields
        valid_attention_fields = {
            "retrieval_weight", "rerank_boost", "context_window", 
            "max_chunks", "prefer_recent", "cross_dept_allowed"
        }
        attention_data = {k: v for k, v in attention_data.items() if k in valid_attention_fields}
        
        # Filter crawler_data to only known fields
        valid_crawler_fields = {
            "enabled", "seed_urls", "max_pages", "max_depth", "schedule", "ttl_days"
        }
        crawler_data = {k: v for k, v in crawler_data.items() if k in valid_crawler_fields}
        
        # Handle "classification" as alias for "sensitivity"
        sensitivity_str = data.get("sensitivity", data.get("classification", "internal"))
        if isinstance(sensitivity_str, str):
            sensitivity_str = sensitivity_str.lower().replace(" ", "_")
        
        # Map common classification names
        sensitivity_map = {
            "public": "public",
            "internal": "internal",
            "confidential": "confidential",
            "restricted": "restricted",
            "hipaa": "hipaa_phi",
            "hipaa_phi": "hipaa_phi",
            "general": "internal",
        }
        sensitivity_str = sensitivity_map.get(sensitivity_str, "internal")
        
        return cls(
            dept_id=dept_id,
            display_name=data.get("display_name", dept_id.title()),
            namespace=data.get("namespace", dept_id),
            sensitivity=SensitivityLevel(sensitivity_str),
            description=data.get("description", ""),
            document_types=data.get("document_types", ["general"]),
            dedicated_nodes=data.get("dedicated_nodes", False),
            pod_type=data.get("pod_type", "p1.x1"),
            attention_profile=AttentionProfile(**attention_data) if attention_data else AttentionProfile(),
            web_crawler=WebCrawlerConfig(**crawler_data) if crawler_data else WebCrawlerConfig(),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            created_by=data.get("created_by", "system"),
            active=data.get("active", True),
        )


class DepartmentManager:
    """
    Manages department configurations with persistence.
    """
    
    def __init__(
        self,
        registry_path: Optional[Path] = None,
        tenant_id: str = "huron",
        auto_create_namespace: bool = True,
    ):
        """
        Initialize department manager.
        
        Args:
            registry_path: Path to YAML registry file
            tenant_id: Default tenant ID
            auto_create_namespace: Auto-provision Pinecone namespace on create
        """
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self.tenant_id = tenant_id
        self.auto_create_namespace = auto_create_namespace
        
        # Load existing registry
        self._registry: Dict[str, Any] = {}
        self._departments: Dict[str, Department] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load department registry from YAML file"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    self._registry = yaml.safe_load(f) or {}
                
                # Parse departments
                for dept_id, dept_data in self._registry.get("departments", {}).items():
                    self._departments[dept_id] = Department.from_dict(dept_id, dept_data)
                
                logger.info(f"Loaded {len(self._departments)} departments from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self._registry = {"departments": {}}
        else:
            logger.info("No registry file found, starting with empty registry")
            self._registry = {"departments": {}}
    
    def _save_registry(self) -> None:
        """Save department registry to YAML file"""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update registry with current departments
            self._registry["departments"] = {
                dept_id: dept.to_dict()
                for dept_id, dept in self._departments.items()
            }
            
            # Preserve other registry sections
            self._registry["last_updated"] = datetime.utcnow().isoformat()
            
            with open(self.registry_path, "w") as f:
                yaml.dump(self._registry, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved registry with {len(self._departments)} departments")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            raise
    
    def create_department(
        self,
        dept_id: str,
        display_name: str,
        sensitivity: str = "internal",
        description: str = "",
        document_types: Optional[List[str]] = None,
        dedicated_nodes: bool = False,
        seed_urls: Optional[List[str]] = None,
        created_by: str = "admin",
        **kwargs
    ) -> Department:
        """
        Create a new department.
        
        Args:
            dept_id: Unique department identifier (lowercase, alphanumeric)
            display_name: Human-readable name
            sensitivity: Sensitivity level (public, internal, confidential, restricted, hipaa_phi)
            description: Department description
            document_types: Supported document types
            dedicated_nodes: Whether to use dedicated Pinecone nodes
            seed_urls: URLs for web crawler
            created_by: Username of creator
        
        Returns:
            Created Department object
        
        Raises:
            ValueError: If dept_id already exists or is invalid
        """
        # Validate dept_id
        dept_id = dept_id.lower().strip()
        if not dept_id.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid dept_id: {dept_id}. Use alphanumeric with _ or -")
        
        if dept_id in self._departments:
            raise ValueError(f"Department {dept_id} already exists")
        
        # Generate namespace
        namespace = f"{dept_id}"
        
        # Create web crawler config
        crawler_config = WebCrawlerConfig(
            enabled=bool(seed_urls),
            seed_urls=seed_urls or [],
        )
        
        # Create department
        department = Department(
            dept_id=dept_id,
            display_name=display_name,
            namespace=namespace,
            sensitivity=SensitivityLevel(sensitivity),
            description=description,
            document_types=document_types or ["general"],
            dedicated_nodes=dedicated_nodes,
            web_crawler=crawler_config,
            created_by=created_by,
        )
        
        # Add to registry
        self._departments[dept_id] = department
        self._save_registry()
        
        # Auto-provision namespace if enabled
        if self.auto_create_namespace:
            self._provision_namespace(department)
        
        logger.info(f"Created department: {dept_id} ({display_name})")
        return department
    
    def update_department(
        self,
        dept_id: str,
        **updates
    ) -> Department:
        """
        Update an existing department.
        
        Args:
            dept_id: Department to update
            **updates: Fields to update
        
        Returns:
            Updated Department object
        """
        if dept_id not in self._departments:
            raise ValueError(f"Department {dept_id} not found")
        
        dept = self._departments[dept_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(dept, key):
                if key == "sensitivity":
                    value = SensitivityLevel(value)
                setattr(dept, key, value)
        
        self._save_registry()
        logger.info(f"Updated department: {dept_id}")
        return dept
    
    def delete_department(self, dept_id: str, soft_delete: bool = True) -> bool:
        """
        Delete a department.
        
        Args:
            dept_id: Department to delete
            soft_delete: If True, mark as inactive; if False, remove entirely
        
        Returns:
            True if successful
        """
        if dept_id not in self._departments:
            raise ValueError(f"Department {dept_id} not found")
        
        if soft_delete:
            self._departments[dept_id].active = False
        else:
            del self._departments[dept_id]
        
        self._save_registry()
        logger.info(f"{'Deactivated' if soft_delete else 'Deleted'} department: {dept_id}")
        return True
    
    def get_department(self, dept_id: str) -> Optional[Department]:
        """Get a department by ID"""
        return self._departments.get(dept_id)
    
    def list_departments(self, include_inactive: bool = False) -> List[Department]:
        """
        List all departments.
        
        Args:
            include_inactive: Include inactive departments
        
        Returns:
            List of Department objects
        """
        if include_inactive:
            return list(self._departments.values())
        return [d for d in self._departments.values() if d.active]
    
    def get_department_ids(self, include_inactive: bool = False) -> List[str]:
        """Get list of department IDs"""
        return [d.dept_id for d in self.list_departments(include_inactive)]
    
    def get_namespace(self, dept_id: str, doc_type: str = "general") -> str:
        """
        Get full Pinecone namespace for a department.
        
        Returns:
            Namespace string (e.g., "vaultmind-huron-legal-general")
        """
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department {dept_id} not found")
        
        import re
        namespace = f"vaultmind-{self.tenant_id}-{dept.namespace}-{doc_type}"
        return re.sub(r"[^a-z0-9-]", "-", namespace.lower())[:45]
    
    def get_attention_profile(self, dept_id: str) -> Optional[AttentionProfile]:
        """Get attention profile for a department"""
        dept = self.get_department(dept_id)
        return dept.attention_profile if dept else None
    
    def _provision_namespace(self, department: Department) -> bool:
        """
        Provision Pinecone namespace for a department.
        
        Note: Pinecone namespaces are created implicitly on first upsert,
        but this method can be extended for explicit provisioning.
        """
        try:
            # Namespaces are created implicitly in Pinecone
            # This is a placeholder for any pre-provisioning logic
            logger.info(f"Namespace ready for department: {department.dept_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to provision namespace: {e}")
            return False
    
    def export_config(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Export department configuration as JSON"""
        config = {
            "tenant_id": self.tenant_id,
            "departments": {
                dept_id: dept.to_dict()
                for dept_id, dept in self._departments.items()
            },
            "exported_at": datetime.utcnow().isoformat(),
        }
        
        if output_path:
            with open(output_path, "w") as f:
                json.dump(config, f, indent=2)
        
        return config
    
    def import_config(self, config: Dict[str, Any], merge: bool = True) -> int:
        """
        Import department configuration.
        
        Args:
            config: Configuration dictionary
            merge: If True, merge with existing; if False, replace
        
        Returns:
            Number of departments imported
        """
        if not merge:
            self._departments.clear()
        
        count = 0
        for dept_id, dept_data in config.get("departments", {}).items():
            if dept_id not in self._departments:
                self._departments[dept_id] = Department.from_dict(dept_id, dept_data)
                count += 1
        
        self._save_registry()
        return count


# Singleton instance
_manager_instance: Optional[DepartmentManager] = None


def get_department_manager() -> DepartmentManager:
    """Get singleton department manager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DepartmentManager()
    return _manager_instance


# Convenience functions
def create_department(dept_id: str, display_name: str, **kwargs) -> Department:
    """Create a new department"""
    return get_department_manager().create_department(dept_id, display_name, **kwargs)


def list_departments(include_inactive: bool = False) -> List[Department]:
    """List all departments"""
    return get_department_manager().list_departments(include_inactive)


def get_department(dept_id: str) -> Optional[Department]:
    """Get a department by ID"""
    return get_department_manager().get_department(dept_id)
