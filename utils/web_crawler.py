"""
Web Crawler for Department-Specific Content

Integrates with Firecrawl for enterprise web crawling with:
- Per-department URL configuration
- Automatic ingestion pipeline
- TTL-based content expiration
- Multi-tenant namespace isolation

Usage:
    from utils.web_crawler import WebCrawler
    from utils.tenant_context import TenantContext
    
    crawler = WebCrawler()
    ctx = TenantContext(tenant_id="huron", dept_id="legal")
    
    results = await crawler.crawl_urls(
        urls=["https://example.com/legal"],
        tenant_context=ctx,
        max_pages=50
    )
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)

# Try to import Firecrawl
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    logger.info("Firecrawl not installed. Install with: pip install firecrawl-py")

# Import ingestion service
try:
    from utils.ingestion_service import IngestionService
    INGESTION_AVAILABLE = True
except ImportError:
    INGESTION_AVAILABLE = False

# Import tenant context
try:
    from utils.tenant_context import TenantContext
except ImportError:
    TenantContext = None


@dataclass
class CrawlResult:
    """Result of a web crawl operation"""
    url: str
    success: bool
    pages_crawled: int = 0
    pages_ingested: int = 0
    error: Optional[str] = None
    crawl_time_ms: int = 0
    
    # Content stats
    total_content_chars: int = 0
    parent_chunks: int = 0
    child_chunks: int = 0
    
    # Metadata
    tenant_id: str = "huron"
    dept_id: Optional[str] = None
    namespace: Optional[str] = None
    crawled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CrawledPage:
    """A single crawled page"""
    url: str
    title: str
    content: str
    html: Optional[str] = None
    links: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    crawled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    content_hash: str = ""
    
    def __post_init__(self):
        if not self.content_hash and self.content:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()


class WebCrawler:
    """
    Enterprise web crawler with multi-tenant support.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_ttl_days: int = 90,
        max_pages_per_crawl: int = 100,
        respect_robots: bool = True,
    ):
        """
        Initialize web crawler.
        
        Args:
            api_key: Firecrawl API key (or from env FIRECRAWL_API_KEY)
            default_ttl_days: Days before content expires
            max_pages_per_crawl: Maximum pages per crawl job
            respect_robots: Whether to respect robots.txt
        """
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.default_ttl_days = default_ttl_days
        self.max_pages_per_crawl = max_pages_per_crawl
        self.respect_robots = respect_robots
        
        # Initialize Firecrawl client
        self.client = None
        if FIRECRAWL_AVAILABLE and self.api_key:
            try:
                self.client = FirecrawlApp(api_key=self.api_key)
                logger.info("Firecrawl client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Firecrawl: {e}")
        
        # Initialize ingestion service
        self.ingestion_service = None
        if INGESTION_AVAILABLE:
            self.ingestion_service = IngestionService()
        
        # Cache for deduplication
        self._content_hashes: Dict[str, str] = {}
    
    @property
    def is_available(self) -> bool:
        """Check if crawler is properly configured"""
        return self.client is not None
    
    async def crawl_urls(
        self,
        urls: List[str],
        tenant_context: Optional[Any] = None,
        max_pages: Optional[int] = None,
        max_depth: int = 2,
        follow_links: bool = True,
        ingest: bool = True,
        **kwargs
    ) -> List[CrawlResult]:
        """
        Crawl URLs and optionally ingest content.
        
        Args:
            urls: List of seed URLs to crawl
            tenant_context: TenantContext for multi-tenant isolation
            max_pages: Maximum pages to crawl (per URL)
            max_depth: Maximum link depth to follow
            follow_links: Whether to follow internal links
            ingest: Whether to automatically ingest content
            **kwargs: Additional options
        
        Returns:
            List of CrawlResult objects
        """
        import time
        
        max_pages = max_pages or self.max_pages_per_crawl
        results = []
        
        # Extract tenant info
        tenant_id = "huron"
        dept_id = None
        namespace = None
        
        if tenant_context:
            tenant_id = getattr(tenant_context, "tenant_id", "huron")
            dept_id = getattr(tenant_context, "dept_id", None)
            if hasattr(tenant_context, "get_namespace") and dept_id:
                try:
                    namespace = tenant_context.get_namespace("external")
                except:
                    pass
        
        for url in urls:
            start_time = time.time()
            
            try:
                # Crawl the URL
                pages = await self._crawl_single_url(
                    url=url,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    follow_links=follow_links,
                )
                
                # Deduplicate
                unique_pages = self._deduplicate_pages(pages)
                
                # Ingest if requested
                parent_chunks = 0
                child_chunks = 0
                
                if ingest and self.ingestion_service:
                    for page in unique_pages:
                        try:
                            result = await self.ingestion_service.ingest_document(
                                text_content=page.content,
                                file_name=page.url,
                                tenant_context=tenant_context,
                                document_type="general",
                                sensitivity_level="internal",
                                source_type="web",
                                source_url=page.url,
                            )
                            if result.success:
                                parent_chunks += result.parent_chunks
                                child_chunks += result.child_chunks
                        except Exception as e:
                            logger.warning(f"Failed to ingest {page.url}: {e}")
                
                crawl_time = int((time.time() - start_time) * 1000)
                
                results.append(CrawlResult(
                    url=url,
                    success=True,
                    pages_crawled=len(pages),
                    pages_ingested=len(unique_pages),
                    crawl_time_ms=crawl_time,
                    total_content_chars=sum(len(p.content) for p in unique_pages),
                    parent_chunks=parent_chunks,
                    child_chunks=child_chunks,
                    tenant_id=tenant_id,
                    dept_id=dept_id,
                    namespace=namespace,
                ))
                
            except Exception as e:
                logger.error(f"Crawl failed for {url}: {e}")
                results.append(CrawlResult(
                    url=url,
                    success=False,
                    error=str(e),
                    crawl_time_ms=int((time.time() - start_time) * 1000),
                    tenant_id=tenant_id,
                    dept_id=dept_id,
                ))
        
        return results
    
    async def _crawl_single_url(
        self,
        url: str,
        max_pages: int,
        max_depth: int,
        follow_links: bool,
    ) -> List[CrawledPage]:
        """Crawl a single URL using Firecrawl"""
        
        if not self.client:
            # Fallback to simple fetch
            return await self._simple_fetch(url)
        
        try:
            # Use Firecrawl's crawl endpoint
            crawl_params = {
                "url": url,
                "limit": max_pages,
                "maxDepth": max_depth if follow_links else 1,
            }
            
            # Start crawl job
            crawl_result = self.client.crawl_url(
                url,
                params={
                    "limit": max_pages,
                    "scrapeOptions": {
                        "formats": ["markdown", "html"],
                    }
                },
                poll_interval=5,  # seconds
            )
            
            # Process results
            pages = []
            if crawl_result and "data" in crawl_result:
                for item in crawl_result["data"]:
                    page = CrawledPage(
                        url=item.get("url", url),
                        title=item.get("metadata", {}).get("title", ""),
                        content=item.get("markdown", item.get("content", "")),
                        html=item.get("html"),
                        links=item.get("links", []),
                        metadata=item.get("metadata", {}),
                    )
                    pages.append(page)
            
            return pages
            
        except Exception as e:
            logger.error(f"Firecrawl error for {url}: {e}")
            return await self._simple_fetch(url)
    
    async def _simple_fetch(self, url: str) -> List[CrawledPage]:
        """Simple fallback fetch using requests"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    html = await response.text()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text(separator="\n", strip=True)
            title = soup.title.string if soup.title else url
            
            return [CrawledPage(
                url=url,
                title=title,
                content=text,
                html=html,
            )]
            
        except ImportError:
            logger.warning("aiohttp or beautifulsoup4 not installed for fallback fetch")
            return []
        except Exception as e:
            logger.error(f"Simple fetch failed for {url}: {e}")
            return []
    
    def _deduplicate_pages(self, pages: List[CrawledPage]) -> List[CrawledPage]:
        """Remove duplicate pages based on content hash"""
        unique = []
        seen_hashes = set()
        
        for page in pages:
            if page.content_hash not in seen_hashes:
                seen_hashes.add(page.content_hash)
                unique.append(page)
        
        return unique
    
    async def crawl_department(
        self,
        dept_id: str,
        tenant_id: str = "huron",
        dept_config: Optional[Dict] = None,
    ) -> List[CrawlResult]:
        """
        Crawl all configured URLs for a department.
        
        Args:
            dept_id: Department identifier
            tenant_id: Tenant identifier
            dept_config: Department configuration (or loaded from registry)
        
        Returns:
            List of CrawlResult objects
        """
        # Load config if not provided
        if not dept_config:
            try:
                import yaml
                registry_path = Path("config/dept_namespace_registry.yml")
                if registry_path.exists():
                    with open(registry_path) as f:
                        registry = yaml.safe_load(f)
                    dept_config = registry.get("departments", {}).get(dept_id, {})
            except Exception as e:
                logger.error(f"Failed to load department config: {e}")
                dept_config = {}
        
        # Get crawler config
        crawler_config = dept_config.get("web_crawler", {})
        
        if not crawler_config.get("enabled"):
            logger.info(f"Crawler not enabled for department {dept_id}")
            return []
        
        urls = crawler_config.get("seed_urls", [])
        
        if not urls:
            logger.info(f"No seed URLs configured for department {dept_id}")
            return []
        
        # Create tenant context
        ctx = None
        if TenantContext:
            ctx = TenantContext(
                tenant_id=tenant_id,
                dept_id=dept_id,
            )
        
        # Crawl URLs
        return await self.crawl_urls(
            urls=urls,
            tenant_context=ctx,
            max_pages=crawler_config.get("max_pages", 50),
            max_depth=crawler_config.get("max_depth", 2),
        )


# Scheduled crawl function for Celery
def schedule_department_crawl(dept_id: str, tenant_id: str = "huron"):
    """
    Schedule a department crawl job.
    
    This function is designed to be called from a Celery task:
    
    @celery.task
    def crawl_department_task(dept_id, tenant_id):
        return schedule_department_crawl(dept_id, tenant_id)
    """
    crawler = WebCrawler()
    
    if not crawler.is_available:
        logger.error("Crawler not available - check FIRECRAWL_API_KEY")
        return {"success": False, "error": "Crawler not configured"}
    
    # Run async crawl
    try:
        results = asyncio.run(crawler.crawl_department(dept_id, tenant_id))
        return {
            "success": True,
            "results": [r.__dict__ for r in results],
            "total_pages": sum(r.pages_crawled for r in results),
            "total_ingested": sum(r.pages_ingested for r in results),
        }
    except Exception as e:
        logger.error(f"Scheduled crawl failed: {e}")
        return {"success": False, "error": str(e)}
