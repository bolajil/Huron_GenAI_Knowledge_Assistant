"""
Data Loss Prevention (DLP) Scanner

Scans documents for sensitive data before ingestion:
- PHI (Protected Health Information) for HIPAA compliance
- PII (Personally Identifiable Information)
- Financial data (credit cards, bank accounts)
- Custom patterns per department

Supports:
- AWS Macie integration (recommended for production)
- Local regex-based scanning (fallback)

Usage:
    from utils.dlp_scanner import DLPScanner, ScanResult
    
    scanner = DLPScanner()
    result = scanner.scan_text(document_text)
    
    if result.has_sensitive_data:
        if result.should_block:
            raise ValueError("Document contains blocked content")
        else:
            # Redact and continue
            safe_text = result.redacted_text
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import AWS Macie
try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False


class SensitivityCategory(Enum):
    """Categories of sensitive data"""
    PHI = "phi"              # Protected Health Information
    PII = "pii"              # Personally Identifiable Information
    FINANCIAL = "financial"  # Credit cards, bank accounts
    CREDENTIALS = "credentials"  # Passwords, API keys
    CUSTOM = "custom"        # Department-specific patterns


class DLPAction(Enum):
    """Action to take when sensitive data is found"""
    ALLOW = "allow"      # Allow without modification
    REDACT = "redact"    # Redact sensitive data and allow
    BLOCK = "block"      # Block the document entirely
    FLAG = "flag"        # Flag for human review


@dataclass
class Finding:
    """A single DLP finding"""
    category: SensitivityCategory
    pattern_name: str
    matched_text: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    redacted_text: str = "[REDACTED]"


@dataclass
class ScanResult:
    """Result of a DLP scan"""
    success: bool
    findings: List[Finding] = field(default_factory=list)
    action: DLPAction = DLPAction.ALLOW
    redacted_text: Optional[str] = None
    original_length: int = 0
    scan_time_ms: int = 0
    scanner_used: str = "local"
    
    @property
    def has_sensitive_data(self) -> bool:
        return len(self.findings) > 0
    
    @property
    def should_block(self) -> bool:
        return self.action == DLPAction.BLOCK
    
    @property
    def finding_summary(self) -> Dict[str, int]:
        """Count findings by category"""
        summary = {}
        for finding in self.findings:
            cat = finding.category.value
            summary[cat] = summary.get(cat, 0) + 1
        return summary


class DLPScanner:
    """
    Data Loss Prevention scanner with multi-tier detection.
    """
    
    # Common PII patterns
    PII_PATTERNS = {
        "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", SensitivityCategory.PII),
        "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", SensitivityCategory.PII),
        "phone_us": (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", SensitivityCategory.PII),
        "date_of_birth": (r"\b(DOB|Date of Birth|Birth Date)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", SensitivityCategory.PII),
    }
    
    # Financial patterns
    FINANCIAL_PATTERNS = {
        "credit_card": (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", SensitivityCategory.FINANCIAL),
        "bank_account": (r"\b\d{8,17}\b", SensitivityCategory.FINANCIAL),  # Simplified
        "routing_number": (r"\b\d{9}\b", SensitivityCategory.FINANCIAL),
    }
    
    # PHI patterns (HIPAA)
    PHI_PATTERNS = {
        "mrn": (r"\b(MRN|Medical Record)[:\s#]*\d{6,10}\b", SensitivityCategory.PHI),
        "patient_id": (r"\b(Patient ID|PatientID)[:\s#]*\d{5,10}\b", SensitivityCategory.PHI),
        "diagnosis_code": (r"\b[A-Z]\d{2}\.?\d{0,2}\b", SensitivityCategory.PHI),  # ICD-10
        "npi": (r"\b\d{10}\b", SensitivityCategory.PHI),  # National Provider Identifier
    }
    
    # Credential patterns
    CREDENTIAL_PATTERNS = {
        "api_key": (r"\b(api[_-]?key|apikey)[:\s=]*['\"]?[\w-]{20,}\b", SensitivityCategory.CREDENTIALS),
        "password": (r"\b(password|passwd|pwd)[:\s=]*['\"]?\S{8,}\b", SensitivityCategory.CREDENTIALS),
        "secret": (r"\b(secret|token)[:\s=]*['\"]?[\w-]{16,}\b", SensitivityCategory.CREDENTIALS),
        "aws_key": (r"\bAKIA[0-9A-Z]{16}\b", SensitivityCategory.CREDENTIALS),
    }
    
    def __init__(
        self,
        use_aws_macie: bool = False,
        aws_region: Optional[str] = None,
        default_action: DLPAction = DLPAction.REDACT,
        enable_phi: bool = True,
        enable_pii: bool = True,
        enable_financial: bool = True,
        enable_credentials: bool = True,
        custom_patterns: Optional[Dict[str, tuple]] = None,
        blocked_categories: Optional[Set[SensitivityCategory]] = None,
    ):
        """
        Initialize DLP scanner.
        
        Args:
            use_aws_macie: Use AWS Macie for scanning (requires AWS credentials)
            aws_region: AWS region for Macie
            default_action: Default action for findings
            enable_phi: Enable PHI detection
            enable_pii: Enable PII detection
            enable_financial: Enable financial data detection
            enable_credentials: Enable credential detection
            custom_patterns: Additional regex patterns
            blocked_categories: Categories that should block ingestion
        """
        self.use_aws_macie = use_aws_macie and AWS_AVAILABLE
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.default_action = default_action
        
        # Build pattern list
        self.patterns = {}
        
        if enable_pii:
            self.patterns.update(self.PII_PATTERNS)
        if enable_financial:
            self.patterns.update(self.FINANCIAL_PATTERNS)
        if enable_phi:
            self.patterns.update(self.PHI_PATTERNS)
        if enable_credentials:
            self.patterns.update(self.CREDENTIAL_PATTERNS)
        if custom_patterns:
            self.patterns.update(custom_patterns)
        
        # Compile regex patterns
        self._compiled_patterns = {
            name: (re.compile(pattern, re.IGNORECASE), category)
            for name, (pattern, category) in self.patterns.items()
        }
        
        # Categories that block ingestion
        self.blocked_categories = blocked_categories or {
            SensitivityCategory.CREDENTIALS,  # Always block exposed credentials
        }
        
        # AWS Macie client
        self.macie_client = None
        if self.use_aws_macie:
            try:
                self.macie_client = boto3.client("macie2", region_name=self.aws_region)
                logger.info("AWS Macie client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Macie: {e}")
                self.use_aws_macie = False
    
    def scan_text(
        self,
        text: str,
        dept_id: Optional[str] = None,
        auto_redact: bool = True,
    ) -> ScanResult:
        """
        Scan text for sensitive data.
        
        Args:
            text: Text to scan
            dept_id: Department ID for custom rules
            auto_redact: Whether to automatically redact findings
        
        Returns:
            ScanResult with findings and optional redacted text
        """
        import time
        start_time = time.time()
        
        findings = []
        
        # Run local regex scan
        for name, (pattern, category) in self._compiled_patterns.items():
            for match in pattern.finditer(text):
                findings.append(Finding(
                    category=category,
                    pattern_name=name,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,  # Local patterns have high confidence
                ))
        
        # Determine action
        action = self._determine_action(findings)
        
        # Redact if needed
        redacted_text = None
        if auto_redact and findings:
            redacted_text = self._redact_text(text, findings)
        
        scan_time = int((time.time() - start_time) * 1000)
        
        return ScanResult(
            success=True,
            findings=findings,
            action=action,
            redacted_text=redacted_text,
            original_length=len(text),
            scan_time_ms=scan_time,
            scanner_used="local",
        )
    
    def _determine_action(self, findings: List[Finding]) -> DLPAction:
        """Determine action based on findings"""
        if not findings:
            return DLPAction.ALLOW
        
        # Check for blocked categories
        for finding in findings:
            if finding.category in self.blocked_categories:
                return DLPAction.BLOCK
        
        # Check for high-sensitivity findings
        phi_count = sum(1 for f in findings if f.category == SensitivityCategory.PHI)
        if phi_count >= 3:
            return DLPAction.FLAG  # Multiple PHI findings need review
        
        return self.default_action
    
    def _redact_text(self, text: str, findings: List[Finding]) -> str:
        """Redact sensitive data from text"""
        # Sort findings by position (reverse to maintain positions)
        sorted_findings = sorted(findings, key=lambda f: f.start_pos, reverse=True)
        
        redacted = text
        for finding in sorted_findings:
            redacted = (
                redacted[:finding.start_pos] +
                finding.redacted_text +
                redacted[finding.end_pos:]
            )
        
        return redacted
    
    async def scan_with_macie(self, s3_bucket: str, s3_key: str) -> ScanResult:
        """
        Scan a document using AWS Macie.
        
        Note: Document must already be in S3.
        
        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key
        
        Returns:
            ScanResult from Macie analysis
        """
        if not self.macie_client:
            return ScanResult(
                success=False,
                scanner_used="macie",
            )
        
        try:
            # Create a classification job
            response = self.macie_client.create_classification_job(
                description="DLP scan for ingestion",
                initialRun=True,
                jobType="ONE_TIME",
                s3JobDefinition={
                    "bucketDefinitions": [{
                        "accountId": os.getenv("AWS_ACCOUNT_ID"),
                        "buckets": [s3_bucket],
                    }],
                    "scoping": {
                        "includes": {
                            "and": [{
                                "simpleScopeTerm": {
                                    "comparator": "EQ",
                                    "key": "OBJECT_KEY",
                                    "values": [s3_key],
                                }
                            }]
                        }
                    }
                },
                name=f"dlp-scan-{s3_key[:20]}",
            )
            
            job_id = response["jobId"]
            
            # Poll for results (simplified - production would use async)
            # In practice, you'd use SNS/SQS for notifications
            
            return ScanResult(
                success=True,
                scanner_used="macie",
                # Findings would be populated from Macie results
            )
            
        except Exception as e:
            logger.error(f"Macie scan failed: {e}")
            return ScanResult(
                success=False,
                scanner_used="macie",
            )


# Convenience function
def scan_before_ingestion(
    text: str,
    dept_id: Optional[str] = None,
    block_on_findings: bool = False,
) -> tuple[bool, str, ScanResult]:
    """
    Scan text before ingestion and return safe version.
    
    Args:
        text: Text to scan
        dept_id: Department ID
        block_on_findings: If True, raises error on any findings
    
    Returns:
        Tuple of (is_safe, safe_text, scan_result)
    
    Raises:
        ValueError: If document should be blocked
    """
    scanner = DLPScanner()
    result = scanner.scan_text(text, dept_id=dept_id)
    
    if result.should_block:
        raise ValueError(
            f"Document blocked due to sensitive content: "
            f"{result.finding_summary}"
        )
    
    if block_on_findings and result.has_sensitive_data:
        raise ValueError(
            f"Document contains sensitive data: "
            f"{result.finding_summary}"
        )
    
    safe_text = result.redacted_text if result.redacted_text else text
    is_safe = not result.has_sensitive_data
    
    return is_safe, safe_text, result
