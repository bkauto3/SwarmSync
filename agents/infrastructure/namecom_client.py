"""
Name.com API Client for Domain Registration and Management
Author: Genesis AI
Date: November 14, 2025
Integration #73: Domain Name Agent
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class DomainAvailability:
    """Domain availability check result"""
    domain: str
    available: bool
    price: float
    premium: bool
    purchasable: bool
    error: Optional[str] = None


@dataclass
class DomainRegistration:
    """Domain registration result"""
    domain: str
    success: bool
    order_id: Optional[str] = None
    total_cost: float = 0.0
    expires_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DNSRecord:
    """DNS record for domain configuration"""
    domain: str
    host: str
    record_type: str  # A, AAAA, CNAME, MX, TXT, etc.
    answer: str
    ttl: int = 300


class NameComClient:
    """
    Name.com API v4 client for domain operations

    Features:
    - Domain availability checking
    - Domain registration with auto-renewal
    - DNS record management
    - GitHub Pages integration
    - Cost tracking and alerts

    API Docs: https://www.name.com/api-docs/
    """

    def __init__(
        self,
        username: Optional[str] = None,
        token: Optional[str] = None,
        endpoint: Optional[str] = None,
        use_test_credentials: bool = False
    ):
        """
        Initialize Name.com API client

        Args:
            username: API username (defaults to env NAMECOM_API_USERNAME)
            token: API token (defaults to env NAMECOM_API_TOKEN)
            endpoint: API endpoint (defaults to env NAMECOM_API_ENDPOINT)
            use_test_credentials: Use test credentials instead of production
        """
        if use_test_credentials:
            self.username = username or os.getenv("NAMECOM_TEST_USERNAME")
            self.token = token or os.getenv("NAMECOM_TEST_TOKEN")
        else:
            self.username = username or os.getenv("NAMECOM_API_USERNAME")
            self.token = token or os.getenv("NAMECOM_API_TOKEN")

        self.endpoint = endpoint or os.getenv("NAMECOM_API_ENDPOINT", "https://api.name.com/v4")

        if not self.username or not self.token:
            raise ValueError(
                "Name.com credentials not found. Set NAMECOM_API_USERNAME and "
                "NAMECOM_API_TOKEN in .env file or pass as arguments."
            )

        self.session = requests.Session()
        self.session.auth = (self.username, self.token)
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Genesis-AI-Domain-Agent/1.0"
        })

        logger.info(f"NameComClient initialized (endpoint={self.endpoint})")

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Name.com API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "/domains/search")
            data: JSON payload for POST/PUT
            params: URL query parameters
            retry_count: Number of retries on failure

        Returns:
            API response as dict

        Raises:
            requests.HTTPError: On API error
        """
        url = f"{self.endpoint}{path}"

        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                return response.json() if response.content else {}

            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt+1}/{retry_count}")
                    time.sleep(wait_time)
                    continue
                elif response.status_code >= 500 and attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    raise

            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Request failed after {retry_count} attempts: {e}")
                    raise

        raise Exception(f"Request failed after {retry_count} retries")

    def check_availability(self, domain: str) -> DomainAvailability:
        """
        Check if domain is available for registration

        Args:
            domain: Domain name (e.g., "example.com")

        Returns:
            DomainAvailability object
        """
        try:
            # Name.com search endpoint
            response = self._request("GET", f"/domains:search", params={"domainName": domain})

            result = response.get("results", [{}])[0] if response.get("results") else {}

            return DomainAvailability(
                domain=domain,
                available=result.get("purchasable", False),
                price=float(result.get("purchasePrice", 0)),
                premium=result.get("premium", False),
                purchasable=result.get("purchasable", False),
                error=None
            )

        except Exception as e:
            logger.error(f"Failed to check availability for {domain}: {e}")
            return DomainAvailability(
                domain=domain,
                available=False,
                price=0.0,
                premium=False,
                purchasable=False,
                error=str(e)
            )

    def register_domain(
        self,
        domain: str,
        years: int = 1,
        auto_renew: bool = True,
        privacy: bool = True
    ) -> DomainRegistration:
        """
        Register a domain name

        Args:
            domain: Domain name to register
            years: Registration period (1-10 years)
            auto_renew: Enable auto-renewal
            privacy: Enable WHOIS privacy protection

        Returns:
            DomainRegistration object
        """
        try:
            # Check availability first
            availability = self.check_availability(domain)
            if not availability.purchasable:
                return DomainRegistration(
                    domain=domain,
                    success=False,
                    error=f"Domain not available: {availability.error or 'already registered'}"
                )

            # Register domain
            payload = {
                "domain": {
                    "domainName": domain,
                    "years": years,
                    "autorenewEnabled": auto_renew,
                    "privacyEnabled": privacy
                }
            }

            response = self._request("POST", "/domains", data=payload)

            return DomainRegistration(
                domain=domain,
                success=True,
                order_id=response.get("order", {}).get("orderId"),
                total_cost=float(response.get("order", {}).get("total", 0)),
                expires_at=response.get("domain", {}).get("expireDate"),
                error=None
            )

        except Exception as e:
            logger.error(f"Failed to register {domain}: {e}")
            return DomainRegistration(
                domain=domain,
                success=False,
                error=str(e)
            )

    def set_dns_records(self, domain: str, records: List[DNSRecord]) -> bool:
        """
        Set DNS records for a domain

        Args:
            domain: Domain name
            records: List of DNSRecord objects

        Returns:
            True if successful, False otherwise
        """
        try:
            # Name.com requires domain without TLD for some operations
            # For example, "example.com" stays as "example.com"

            # Get existing records first (to delete them)
            try:
                existing = self._request("GET", f"/domains/{domain}/records")
                for record in existing.get("records", []):
                    record_id = record.get("id")
                    if record_id:
                        self._request("DELETE", f"/domains/{domain}/records/{record_id}")
            except Exception as e:
                logger.warning(f"Could not clear existing DNS records: {e}")

            # Add new records
            for record in records:
                payload = {
                    "host": record.host,
                    "type": record.record_type,
                    "answer": record.answer,
                    "ttl": record.ttl
                }
                self._request("POST", f"/domains/{domain}/records", data=payload)

            logger.info(f"DNS records updated for {domain}: {len(records)} records set")
            return True

        except Exception as e:
            logger.error(f"Failed to set DNS records for {domain}: {e}")
            return False

    def configure_github_pages(
        self,
        domain: str,
        github_pages_ip: str = "185.199.108.153"
    ) -> bool:
        """
        Configure DNS records for GitHub Pages

        GitHub Pages requires:
        - 4 A records pointing to GitHub IPs
        - CNAME record for www subdomain

        Args:
            domain: Domain name (e.g., "example.com")
            github_pages_ip: GitHub Pages IP (default: 185.199.108.153)

        Returns:
            True if successful, False otherwise
        """
        # GitHub Pages IP addresses (as of 2025)
        github_ips = [
            "185.199.108.153",
            "185.199.109.153",
            "185.199.110.153",
            "185.199.111.153"
        ]

        records = []

        # Add A records for apex domain
        for ip in github_ips:
            records.append(DNSRecord(
                domain=domain,
                host="@",  # Apex domain
                record_type="A",
                answer=ip,
                ttl=300
            ))

        # Add CNAME for www subdomain
        records.append(DNSRecord(
            domain=domain,
            host="www",
            record_type="CNAME",
            answer=domain,
            ttl=300
        ))

        return self.set_dns_records(domain, records)

    def get_domain_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered domain

        Args:
            domain: Domain name

        Returns:
            Domain info dict or None if not found
        """
        try:
            response = self._request("GET", f"/domains/{domain}")
            return response.get("domain")
        except Exception as e:
            logger.error(f"Failed to get domain info for {domain}: {e}")
            return None

    def list_domains(self) -> List[Dict[str, Any]]:
        """
        List all domains in the account

        Returns:
            List of domain info dicts
        """
        try:
            response = self._request("GET", "/domains")
            return response.get("domains", [])
        except Exception as e:
            logger.error(f"Failed to list domains: {e}")
            return []


def get_namecom_client(use_test: bool = False) -> NameComClient:
    """
    Factory function to get NameComClient instance

    Args:
        use_test: Use test credentials instead of production

    Returns:
        NameComClient instance
    """
    return NameComClient(use_test_credentials=use_test)


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)

    client = get_namecom_client()

    # Test domain availability
    test_domain = "genesis-ai-test-12345.com"
    print(f"\nChecking availability: {test_domain}")
    result = client.check_availability(test_domain)
    print(f"Available: {result.available}, Price: ${result.price}, Purchasable: {result.purchasable}")

    # List domains
    print("\nListing domains:")
    domains = client.list_domains()
    print(f"Found {len(domains)} domains in account")
