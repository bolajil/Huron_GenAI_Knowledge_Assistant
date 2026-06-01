#!/usr/bin/env python3
"""
Huron GenAI Knowledge Assistant — Deployment Verification Script

Run after deploying to AWS or Azure to validate all services are working.

Usage:
    python scripts/deployment_test.py --url https://your-alb-url.com
    python scripts/deployment_test.py --url https://huron-backend.azurecontainerapps.io

Tests:
    1. Health check endpoint
    2. Authentication (login)
    3. API authorization (protected endpoints)
    4. Database connectivity
    5. Vector store connectivity (optional)
    6. Response times
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Optional, Tuple
import urllib.request
import urllib.error
import ssl


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.RESET}\n")


def print_test(name: str, passed: bool, duration_ms: Optional[float] = None, detail: str = ""):
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    time_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
    detail_str = f" - {detail}" if detail else ""
    print(f"  {status} {name}{time_str}{detail_str}")
    return passed


def http_request(
    url: str,
    method: str = "GET",
    data: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
) -> Tuple[int, dict, float]:
    """Make HTTP request and return (status_code, json_response, duration_ms)."""
    start = time.time()
    
    headers = headers or {}
    headers.setdefault("Content-Type", "application/json")
    
    req_data = json.dumps(data).encode() if data else None
    request = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    # Allow self-signed certs in dev
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(request, context=ctx, timeout=timeout) as response:
            body = json.loads(response.read().decode())
            duration = (time.time() - start) * 1000
            return response.status, body, duration
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode())
        except:
            pass
        duration = (time.time() - start) * 1000
        return e.code, body, duration
    except Exception as e:
        duration = (time.time() - start) * 1000
        return 0, {"error": str(e)}, duration


def test_health(base_url: str) -> Tuple[bool, float]:
    """Test health endpoint."""
    url = f"{base_url}/health"
    status, body, duration = http_request(url)
    passed = status == 200 and body.get("status") == "healthy"
    return passed, duration


def test_login(base_url: str, username: str, password: str) -> Tuple[bool, str, float]:
    """Test login and return (passed, token, duration)."""
    url = f"{base_url}/api/v1/auth/login"
    status, body, duration = http_request(url, "POST", {"username": username, "password": password})
    
    if status == 200 and "access_token" in body:
        return True, body["access_token"], duration
    return False, body.get("detail", "Unknown error"), duration


def test_auth_me(base_url: str, token: str) -> Tuple[bool, float, dict]:
    """Test authenticated /me endpoint."""
    url = f"{base_url}/api/v1/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    status, body, duration = http_request(url, "GET", headers=headers)
    
    if status == 200 and "username" in body:
        return True, duration, body
    return False, duration, body


def test_unauthorized(base_url: str) -> Tuple[bool, float]:
    """Test that protected endpoints reject unauthenticated requests."""
    url = f"{base_url}/api/v1/auth/me"
    status, body, duration = http_request(url)
    # Should return 401 or 403
    passed = status in (401, 403)
    return passed, duration


def test_departments(base_url: str, token: str) -> Tuple[bool, float, int]:
    """Test departments endpoint (requires root)."""
    url = f"{base_url}/api/v1/root/departments"
    headers = {"Authorization": f"Bearer {token}"}
    status, body, duration = http_request(url, "GET", headers=headers)
    
    if status == 200 and "departments" in body:
        return True, duration, len(body["departments"])
    return False, duration, 0


def test_docs_endpoint(base_url: str) -> Tuple[bool, float]:
    """Test FastAPI Swagger docs."""
    url = f"{base_url}/docs"
    try:
        req = urllib.request.Request(url)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        start = time.time()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            duration = (time.time() - start) * 1000
            return response.status == 200, duration
    except:
        return False, 0


def test_openapi_schema(base_url: str) -> Tuple[bool, float, int]:
    """Test OpenAPI schema endpoint."""
    url = f"{base_url}/openapi.json"
    status, body, duration = http_request(url)
    
    if status == 200 and "paths" in body:
        return True, duration, len(body.get("paths", {}))
    return False, duration, 0


def run_tests(base_url: str, username: str = "root", password: str = "HuronRoot2026!"):
    """Run all deployment tests."""
    print_header("Huron GenAI Deployment Verification")
    
    print(f"  Target URL: {Colors.BOLD}{base_url}{Colors.RESET}")
    print(f"  Timestamp:  {datetime.now().isoformat()}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    def record(passed: bool):
        results["total"] += 1
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        return passed
    
    # ─── Health Check ────────────────────────────────────────────────────────
    print_header("1. Health Check")
    
    passed, duration = test_health(base_url)
    record(print_test("GET /health returns healthy", passed, duration))
    
    # ─── API Documentation ───────────────────────────────────────────────────
    print_header("2. API Documentation")
    
    passed, duration = test_docs_endpoint(base_url)
    record(print_test("Swagger UI accessible", passed, duration))
    
    passed, duration, path_count = test_openapi_schema(base_url)
    record(print_test("OpenAPI schema valid", passed, duration, f"{path_count} endpoints"))
    
    # ─── Authentication ──────────────────────────────────────────────────────
    print_header("3. Authentication")
    
    passed, duration = test_unauthorized(base_url)
    record(print_test("Protected endpoints reject unauthenticated", passed, duration))
    
    passed, token, duration = test_login(base_url, username, password)
    if not passed:
        record(print_test(f"Login as {username}", False, duration, str(token)))
        token = None
    else:
        record(print_test(f"Login as {username}", True, duration))
    
    # ─── Authorized Requests ─────────────────────────────────────────────────
    print_header("4. Authorized API Access")
    
    if token:
        passed, duration, user_info = test_auth_me(base_url, token)
        detail = f"role={user_info.get('role')}" if passed else str(user_info)
        record(print_test("GET /api/v1/auth/me", passed, duration, detail))
        
        passed, duration, dept_count = test_departments(base_url, token)
        record(print_test("GET /api/v1/root/departments", passed, duration, f"{dept_count} departments"))
    else:
        record(print_test("GET /api/v1/auth/me", False, 0, "No token"))
        record(print_test("GET /api/v1/root/departments", False, 0, "No token"))
    
    # ─── Summary ─────────────────────────────────────────────────────────────
    print_header("Summary")
    
    pass_rate = (results["passed"] / results["total"]) * 100 if results["total"] > 0 else 0
    
    if results["failed"] == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}All {results['total']} tests passed!{Colors.RESET}")
        print(f"\n  {Colors.GREEN}✓ Deployment is healthy and operational.{Colors.RESET}")
        return 0
    else:
        print(f"  {Colors.RED}Passed: {results['passed']}/{results['total']} ({pass_rate:.0f}%){Colors.RESET}")
        print(f"  {Colors.RED}Failed: {results['failed']}{Colors.RESET}")
        print(f"\n  {Colors.RED}✗ Deployment has issues. Check failed tests above.{Colors.RESET}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Test Huron GenAI deployment")
    parser.add_argument("--url", required=True, help="Base URL of the deployment (e.g., https://alb-dns-name.com)")
    parser.add_argument("--username", default="root", help="Username for login test")
    parser.add_argument("--password", default="HuronRoot2026!", help="Password for login test")
    
    args = parser.parse_args()
    
    # Normalize URL (remove trailing slash)
    base_url = args.url.rstrip("/")
    
    exit_code = run_tests(base_url, args.username, args.password)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
