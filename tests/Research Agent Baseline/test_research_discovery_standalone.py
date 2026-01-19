"""
Standalone test suite for Research Discovery Agent
(Does not trigger analyst_agent imports)
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import directly without going through agents/__init__.py
from agents.research_discovery_agent import (
    ResearchPaper,
    ResearchArea,
    DiscoverySource,
    ArxivCrawler,
    ResearchFilteringEngine,
    ResearchAnalysisEngine,
    ResearchDiscoveryAgent
)


class TestResearchPaper:
    """Test ResearchPaper dataclass"""

    def test_paper_creation(self):
        """Test creating research paper"""
        paper = ResearchPaper(
            arxiv_id="2510.20809",
            title="Real Deep Research",
            abstract="A framework for systematic research analysis",
            authors=["Author 1", "Author 2"],
            published_date="2025-10-23T00:00:00Z",
            source=DiscoverySource.ARXIV,
            research_areas=[ResearchArea.AGENT_SYSTEMS],
            relevance_score=0.95,
            summary="Systematic research analysis framework",
            key_insights=["Insight 1", "Insight 2"],
            implementation_available=True,
            discovered_at=datetime.now().isoformat()
        )

        assert paper.arxiv_id == "2510.20809"
        assert paper.relevance_score == 0.95
        assert len(paper.key_insights) == 2

    def test_paper_to_dict(self):
        """Test converting paper to dictionary"""
        paper = ResearchPaper(
            arxiv_id="2510.20809",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Author"],
            published_date="2025-10-23T00:00:00Z",
            source=DiscoverySource.ARXIV,
            research_areas=[ResearchArea.AGENT_SYSTEMS, ResearchArea.LLM_OPTIMIZATION],
            relevance_score=0.85,
            summary="Test summary",
            key_insights=["Insight"],
            implementation_available=False,
            discovered_at=datetime.now().isoformat()
        )

        data = paper.to_dict()

        assert data['arxiv_id'] == "2510.20809"
        assert data['source'] == "arxiv"
        assert data['research_areas'] == ["agent_systems", "llm_optimization"]

    def test_paper_from_dict(self):
        """Test loading paper from dictionary"""
        data = {
            "arxiv_id": "2510.20809",
            "title": "Test Paper",
            "abstract": "Test abstract",
            "authors": ["Author"],
            "published_date": "2025-10-23T00:00:00Z",
            "source": "arxiv",
            "research_areas": ["agent_systems"],
            "relevance_score": 0.85,
            "summary": "Test summary",
            "key_insights": ["Insight"],
            "implementation_available": False,
            "discovered_at": datetime.now().isoformat(),
            "embedding": None
        }

        paper = ResearchPaper.from_dict(data)

        assert paper.arxiv_id == "2510.20809"
        assert paper.source == DiscoverySource.ARXIV
        assert paper.research_areas[0] == ResearchArea.AGENT_SYSTEMS


class TestArxivCrawler:
    """Test ArXiv crawler"""

    def test_crawler_initialization(self):
        """Test crawler creation"""
        crawler = ArxivCrawler()

        assert crawler.base_url == "http://export.arxiv.org/api/query"
        assert len(crawler.categories) == 5
        assert "cs.AI" in crawler.categories


class TestResearchArea:
    """Test ResearchArea enum"""

    def test_all_areas_defined(self):
        """Test that all 7 research areas are defined"""
        areas = [area for area in ResearchArea]
        assert len(areas) == 7

        expected = [
            ResearchArea.AGENT_SYSTEMS,
            ResearchArea.LLM_OPTIMIZATION,
            ResearchArea.SAFETY_ALIGNMENT,
            ResearchArea.GUI_AUTOMATION,
            ResearchArea.MEMORY_SYSTEMS,
            ResearchArea.ORCHESTRATION,
            ResearchArea.SELF_IMPROVEMENT
        ]

        for area in expected:
            assert area in areas


class TestDiscoverySource:
    """Test DiscoverySource enum"""

    def test_sources_defined(self):
        """Test that discovery sources are defined"""
        assert DiscoverySource.ARXIV.value == "arxiv"
        assert DiscoverySource.CONFERENCE.value == "conference"
        assert DiscoverySource.INDUSTRY.value == "industry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
