"""
Department-Scoped Web Search for VaultMind RAG Pipeline

Extends web search with department-specific domain filtering:
- Legal: regulatory sites, law databases
- Clinical: FDA, CMS, medical journals
- Finance: SEC, IRS, financial databases
- HR: labor department, benefits providers
- IT: tech documentation, security advisories
- Operations: industry standards, compliance sites
- Marketing: industry news, market research

Results are filtered by allowed domains and can be auto-ingested
into the department's external sub-namespace in Pinecone.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import yaml
from pathlib import Path

from utils.web_search import run_web_search, _bing_search, _ddgs_search

logger = logging.getLogger(__name__)

# Department web search profiles
DEFAULT_DEPT_WEB_PROFILES = {
    'legal': {
        'allowed_domains': [
            'law.cornell.edu', 'regulations.gov', 'ecfr.gov',
            'supremecourt.gov', 'uscourts.gov', 'lexisnexis.com',
            'westlaw.com', 'justia.com', 'findlaw.com',
            'sec.gov', 'ftc.gov', 'dol.gov'
        ],
        'blocked_domains': ['wikipedia.org', 'reddit.com'],
        'seed_queries': ['regulatory compliance', 'legal updates'],
        'priority_boost': 1.3
    },
    'clinical': {
        'allowed_domains': [
            'fda.gov', 'cms.gov', 'cdc.gov', 'nih.gov',
            'pubmed.ncbi.nlm.nih.gov', 'clinicaltrials.gov',
            'who.int', 'mayoclinic.org', 'clevelandclinic.org',
            'uptodate.com', 'medscape.com', 'nejm.org'
        ],
        'blocked_domains': ['wikipedia.org', 'webmd.com'],
        'seed_queries': ['clinical guidelines', 'FDA updates'],
        'priority_boost': 1.5,
        'hipaa_filter': True  # Extra filtering for HIPAA compliance
    },
    'finance': {
        'allowed_domains': [
            'sec.gov', 'irs.gov', 'treasury.gov', 'federalreserve.gov',
            'investor.gov', 'finra.org', 'fasb.org', 'gasb.org',
            'bloomberg.com', 'reuters.com', 'wsj.com',
            'fortune.com', 'forbes.com'
        ],
        'blocked_domains': ['wikipedia.org', 'investopedia.com'],
        'seed_queries': ['SEC filings', 'financial regulations'],
        'priority_boost': 1.2
    },
    'hr': {
        'allowed_domains': [
            'dol.gov', 'eeoc.gov', 'osha.gov', 'ssa.gov',
            'shrm.org', 'hr.com', 'bls.gov',
            'healthcare.gov', 'irs.gov'
        ],
        'blocked_domains': ['wikipedia.org'],
        'seed_queries': ['HR compliance', 'employment law'],
        'priority_boost': 1.0
    },
    'it': {
        'allowed_domains': [
            'nist.gov', 'cisa.gov', 'nvd.nist.gov',
            'docs.microsoft.com', 'cloud.google.com', 'aws.amazon.com',
            'kubernetes.io', 'docker.com', 'github.com',
            'stackoverflow.com', 'owasp.org'
        ],
        'blocked_domains': ['w3schools.com'],
        'seed_queries': ['security advisory', 'CVE updates'],
        'priority_boost': 1.1
    },
    'operations': {
        'allowed_domains': [
            'iso.org', 'asq.org', 'bsigroup.com',
            'pmi.org', 'lean.org', 'sixsigma.com',
            'osha.gov', 'epa.gov'
        ],
        'blocked_domains': ['wikipedia.org'],
        'seed_queries': ['compliance standards', 'operational excellence'],
        'priority_boost': 1.0
    },
    'marketing': {
        'allowed_domains': [
            'marketingweek.com', 'adage.com', 'marketingland.com',
            'hubspot.com', 'contentmarketinginstitute.com',
            'searchenginejournal.com', 'moz.com',
            'statista.com', 'emarketer.com'
        ],
        'blocked_domains': [],
        'seed_queries': ['market trends', 'industry analysis'],
        'priority_boost': 0.9
    },
    'general': {
        'allowed_domains': [],  # No restrictions
        'blocked_domains': ['wikipedia.org'],
        'seed_queries': [],
        'priority_boost': 1.0
    }
}


class DeptWebSearcher:
    """
    Department-scoped web search with domain filtering and result ranking.
    """
    
    def __init__(self, config_path: str = None):
        self.profiles = DEFAULT_DEPT_WEB_PROFILES.copy()
        
        # Load custom profiles from config if available
        if config_path:
            self._load_config(config_path)
        else:
            # Try default config location
            default_path = Path(__file__).parent.parent / "config" / "dept_web_profiles.yml"
            if default_path.exists():
                self._load_config(str(default_path))
    
    def _load_config(self, config_path: str):
        """Load department web profiles from YAML config"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if config and 'departments' in config:
                for dept_id, profile in config['departments'].items():
                    if 'web_profile' in profile:
                        self.profiles[dept_id] = {
                            **self.profiles.get(dept_id, {}),
                            **profile['web_profile']
                        }
                logger.info(f"Loaded web profiles from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load web config: {e}")
    
    def search(
        self,
        query: str,
        dept_id: str,
        max_results: int = 10,
        include_all: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Perform department-scoped web search.
        
        Args:
            query: Search query
            dept_id: Department ID for domain filtering
            max_results: Maximum results to return
            include_all: If True, include results from non-allowed domains (marked)
        
        Returns:
            List of search results with dept relevance scores
        """
        profile = self.profiles.get(dept_id, self.profiles['general'])
        allowed_domains = profile.get('allowed_domains', [])
        blocked_domains = profile.get('blocked_domains', [])
        priority_boost = profile.get('priority_boost', 1.0)
        
        # Get raw search results (fetch extra for filtering)
        raw_results = run_web_search(query, max_results * 3)
        
        if not raw_results:
            logger.warning(f"No web results for query: {query}")
            return []
        
        # Filter and score results
        filtered_results = []
        other_results = []
        
        for result in raw_results:
            url = result.get('url', '').lower()
            
            # Check blocked domains
            is_blocked = any(blocked in url for blocked in blocked_domains)
            if is_blocked:
                continue
            
            # Check allowed domains
            is_allowed = not allowed_domains or any(allowed in url for allowed in allowed_domains)
            
            # Add metadata
            enhanced_result = {
                **result,
                'dept_id': dept_id,
                'is_dept_relevant': is_allowed,
                'relevance_score': priority_boost if is_allowed else 0.5,
                'retrieved_at': datetime.now().isoformat(),
                'source_type': 'web_search'
            }
            
            if is_allowed:
                filtered_results.append(enhanced_result)
            elif include_all:
                other_results.append(enhanced_result)
        
        # Sort by relevance
        filtered_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Combine results
        final_results = filtered_results[:max_results]
        
        if include_all and len(final_results) < max_results:
            remaining = max_results - len(final_results)
            final_results.extend(other_results[:remaining])
        
        logger.info(f"Dept web search [{dept_id}]: {len(final_results)} results for '{query}'")
        return final_results
    
    def search_with_seed_queries(
        self,
        dept_id: str,
        custom_query: str = None,
        max_results_per_query: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search using department seed queries plus optional custom query.
        Used for scheduled web crawling/ingestion.
        """
        profile = self.profiles.get(dept_id, self.profiles['general'])
        seed_queries = profile.get('seed_queries', [])
        
        all_results = []
        seen_urls = set()
        
        # Search with each seed query
        for seed_query in seed_queries:
            results = self.search(seed_query, dept_id, max_results_per_query)
            for r in results:
                if r['url'] not in seen_urls:
                    seen_urls.add(r['url'])
                    all_results.append(r)
        
        # Search with custom query if provided
        if custom_query:
            results = self.search(custom_query, dept_id, max_results_per_query)
            for r in results:
                if r['url'] not in seen_urls:
                    seen_urls.add(r['url'])
                    all_results.append(r)
        
        return all_results
    
    def prepare_for_ingestion(
        self,
        results: List[Dict[str, Any]],
        dept_id: str,
        tenant_id: str = "huron"
    ) -> List[Dict[str, Any]]:
        """
        Prepare web search results for ingestion into dept's external namespace.
        
        Returns documents ready for vector store ingestion.
        """
        docs_for_ingestion = []
        
        for result in results:
            doc = {
                'id': f"web_{dept_id}_{hash(result['url'])}",
                'content': f"{result.get('title', '')}\n\n{result.get('snippet', '')}",
                'metadata': {
                    'source': result['url'],
                    'source_type': 'web_search',
                    'title': result.get('title', ''),
                    'dept_id': dept_id,
                    'tenant_id': tenant_id,
                    'namespace': f"vaultmind-{tenant_id}-{dept_id}-external",
                    'retrieved_at': result.get('retrieved_at', datetime.now().isoformat()),
                    'is_dept_relevant': result.get('is_dept_relevant', False),
                    'relevance_score': result.get('relevance_score', 0.5),
                    'ttl_days': 90  # External content expires in 90 days
                }
            }
            docs_for_ingestion.append(doc)
        
        return docs_for_ingestion
    
    def get_profile(self, dept_id: str) -> Dict[str, Any]:
        """Get the web search profile for a department"""
        return self.profiles.get(dept_id, self.profiles['general'])
    
    def update_profile(self, dept_id: str, profile_updates: Dict[str, Any]):
        """Update a department's web search profile"""
        if dept_id not in self.profiles:
            self.profiles[dept_id] = {}
        self.profiles[dept_id].update(profile_updates)


# Global instance
_dept_searcher = None

def get_dept_web_searcher() -> DeptWebSearcher:
    """Get or create global department web searcher"""
    global _dept_searcher
    if _dept_searcher is None:
        _dept_searcher = DeptWebSearcher()
    return _dept_searcher


def dept_web_search(
    query: str,
    dept_id: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Convenience function for department-scoped web search.
    
    Args:
        query: Search query
        dept_id: Department ID (legal, clinical, finance, hr, it, operations, marketing)
        max_results: Maximum results
    
    Returns:
        List of filtered, scored search results
    """
    searcher = get_dept_web_searcher()
    return searcher.search(query, dept_id, max_results)
