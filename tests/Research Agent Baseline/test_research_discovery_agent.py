"""
Test suite for Research Discovery Agent

Tests RDR methodology implementation:
- ArXiv crawling
- LLM-based filtering
- Deep analysis
- MemoryOS integration
- Discovery pipeline
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from agents.research_discovery_agent import (
    ResearchDiscoveryAgent,
    ArxivCrawler,
    ResearchFilteringEngine,
    ResearchAnalysisEngine,
    ResearchPaper,
    ResearchArea,
    DiscoverySource,
    get_research_discovery_agent
)
from infrastructure.llm_client import MockLLMClient


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

    @pytest.mark.asyncio
    async def test_fetch_recent_papers_mock(self):
        """Test fetching papers with mocked feed"""
        crawler = ArxivCrawler()

        # Mock feedparser.parse
        with patch('feedparser.parse') as mock_parse:
            mock_entry = Mock()
            mock_entry.id = "http://arxiv.org/abs/2510.20809"
            mock_entry.title = "Test Paper"
            mock_entry.summary = "Test abstract"
            mock_entry.published = "2025-10-23T00:00:00Z"
            mock_entry.authors = [Mock(name="Author 1")]
            mock_entry.tags = [Mock(term="cs.AI")]

            mock_feed = Mock()
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            papers = await crawler.fetch_recent_papers(days_back=7, max_results=10)

            assert len(papers) > 0
            assert papers[0]['arxiv_id'] == "2510.20809"
            assert papers[0]['title'] == "Test Paper"


class TestResearchFilteringEngine:
    """Test LLM-based filtering"""

    @pytest.mark.asyncio
    async def test_classify_relevant_paper(self):
        """Test classifying relevant paper"""
        # Mock LLM client
        mock_llm = MockLLMClient(mock_responses={
            "agent": {
                "is_relevant": True,
                "research_areas": ["agent_systems", "orchestration"],
                "relevance_score": 0.9,
                "reasoning": "Paper discusses multi-agent orchestration"
            }
        })

        engine = ResearchFilteringEngine(mock_llm)

        result = await engine.classify_paper(
            title="Multi-Agent Orchestration Framework",
            abstract="We propose a framework for orchestrating multiple agents..."
        )

        assert result['is_relevant'] is True
        assert result['relevance_score'] == 0.9
        assert "agent_systems" in result['research_areas']

    @pytest.mark.asyncio
    async def test_classify_irrelevant_paper(self):
        """Test classifying irrelevant paper"""
        mock_llm = MockLLMClient(mock_responses={
            "quantum": {
                "is_relevant": False,
                "research_areas": [],
                "relevance_score": 0.1,
                "reasoning": "Paper focuses on quantum computing, not relevant to agents"
            }
        })

        engine = ResearchFilteringEngine(mock_llm)

        result = await engine.classify_paper(
            title="Quantum Computing Algorithms",
            abstract="We study quantum algorithms for cryptography..."
        )

        assert result['is_relevant'] is False
        assert result['relevance_score'] == 0.1

    @pytest.mark.asyncio
    async def test_classify_error_handling(self):
        """Test error handling in classification"""
        # Mock LLM that raises exception
        mock_llm = Mock()
        mock_llm.generate_structured_output = AsyncMock(side_effect=Exception("API Error"))

        engine = ResearchFilteringEngine(mock_llm)

        result = await engine.classify_paper(
            title="Test Paper",
            abstract="Test abstract"
        )

        assert result['is_relevant'] is False
        assert "Classification error" in result['reasoning']


class TestResearchAnalysisEngine:
    """Test deep analysis engine"""

    @pytest.mark.asyncio
    async def test_analyze_paper(self):
        """Test paper analysis"""
        mock_llm = MockLLMClient(mock_responses={
            "orchestration": {
                "summary": "Paper proposes new orchestration method with 50% improvement",
                "key_insights": [
                    "Uses hierarchical decomposition",
                    "Reduces latency by 50%",
                    "Open-source implementation available"
                ],
                "implementation_available": True
            }
        })

        engine = ResearchAnalysisEngine(mock_llm)

        result = await engine.analyze_paper(
            title="Hierarchical Orchestration",
            abstract="We propose hierarchical orchestration...",
            research_areas=["orchestration"]
        )

        assert "orchestration" in result['summary'].lower()
        assert len(result['key_insights']) == 3
        assert result['implementation_available'] is True

    @pytest.mark.asyncio
    async def test_analyze_error_handling(self):
        """Test error handling in analysis"""
        mock_llm = Mock()
        mock_llm.generate_structured_output = AsyncMock(side_effect=Exception("API Error"))

        engine = ResearchAnalysisEngine(mock_llm)

        result = await engine.analyze_paper(
            title="Test",
            abstract="Test",
            research_areas=[]
        )

        assert "Analysis error" in result['summary']
        assert result['key_insights'] == []


class TestResearchDiscoveryAgent:
    """Test main discovery agent"""

    @pytest.fixture
    def mock_agent(self):
        """Create agent with mock LLM clients"""
        with patch('agents.research_discovery_agent.LLMFactory.create') as mock_factory:
            # Mock Haiku client (filtering)
            mock_haiku = MockLLMClient(mock_responses={
                "test": {
                    "is_relevant": True,
                    "research_areas": ["agent_systems"],
                    "relevance_score": 0.8,
                    "reasoning": "Relevant paper"
                }
            })

            # Mock Sonnet client (analysis)
            mock_sonnet = MockLLMClient(mock_responses={
                "test": {
                    "summary": "Test summary",
                    "key_insights": ["Insight 1", "Insight 2"],
                    "implementation_available": True
                }
            })

            def create_mock(provider, api_key=None):
                if "haiku" in str(provider).lower():
                    return mock_haiku
                else:
                    return mock_sonnet

            mock_factory.side_effect = create_mock

            # Mock MemoryOS
            with patch('agents.research_discovery_agent.create_genesis_memory') as mock_memory:
                mock_memory_instance = Mock()
                mock_memory_instance.store = Mock()
                mock_memory_instance.retrieve = Mock(return_value=[])
                mock_memory.return_value = mock_memory_instance

                agent = ResearchDiscoveryAgent(
                    openai_api_key="test_key",
                    anthropic_api_key="test_key"
                )

                yield agent

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_agent):
        """Test agent initialization"""
        assert mock_agent.crawler is not None
        assert mock_agent.filter_engine is not None
        assert mock_agent.analysis_engine is not None
        assert mock_agent.memory is not None

    @pytest.mark.asyncio
    async def test_discovery_cycle(self, mock_agent):
        """Test full discovery cycle"""
        # Mock crawler
        mock_papers = [
            {
                "arxiv_id": "2510.20809",
                "title": "Test Paper on Agent Systems",
                "abstract": "We propose a multi-agent framework...",
                "authors": ["Author 1"],
                "published_date": "2025-10-23T00:00:00Z",
                "source": "arxiv"
            }
        ]

        with patch.object(mock_agent.crawler, 'fetch_recent_papers', return_value=mock_papers):
            summary = await mock_agent.run_discovery_cycle(
                days_back=7,
                max_papers=10,
                min_relevance_score=0.6
            )

            assert summary['total_fetched'] == 1
            assert summary['total_analyzed'] >= 0
            assert 'top_5_papers' in summary
            assert 'area_breakdown' in summary

    @pytest.mark.asyncio
    async def test_get_top_discoveries(self, mock_agent):
        """Test retrieving top discoveries"""
        # Add mock papers
        mock_agent.discovered_papers = [
            ResearchPaper(
                arxiv_id="1",
                title="Paper 1",
                abstract="Abstract 1",
                authors=["Author"],
                published_date="2025-10-23T00:00:00Z",
                source=DiscoverySource.ARXIV,
                research_areas=[ResearchArea.AGENT_SYSTEMS],
                relevance_score=0.9,
                summary="Summary",
                key_insights=["Insight"],
                implementation_available=True,
                discovered_at=datetime.now().isoformat()
            ),
            ResearchPaper(
                arxiv_id="2",
                title="Paper 2",
                abstract="Abstract 2",
                authors=["Author"],
                published_date="2025-10-23T00:00:00Z",
                source=DiscoverySource.ARXIV,
                research_areas=[ResearchArea.LLM_OPTIMIZATION],
                relevance_score=0.7,
                summary="Summary",
                key_insights=["Insight"],
                implementation_available=False,
                discovered_at=datetime.now().isoformat()
            )
        ]

        # Get top 1
        top = await mock_agent.get_top_discoveries(top_k=1)

        assert len(top) == 1
        assert top[0].relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_get_top_discoveries_with_filter(self, mock_agent):
        """Test retrieving discoveries with area filter"""
        mock_agent.discovered_papers = [
            ResearchPaper(
                arxiv_id="1",
                title="Paper 1",
                abstract="Abstract",
                authors=["Author"],
                published_date="2025-10-23T00:00:00Z",
                source=DiscoverySource.ARXIV,
                research_areas=[ResearchArea.AGENT_SYSTEMS],
                relevance_score=0.9,
                summary="Summary",
                key_insights=["Insight"],
                implementation_available=True,
                discovered_at=datetime.now().isoformat()
            ),
            ResearchPaper(
                arxiv_id="2",
                title="Paper 2",
                abstract="Abstract",
                authors=["Author"],
                published_date="2025-10-23T00:00:00Z",
                source=DiscoverySource.ARXIV,
                research_areas=[ResearchArea.LLM_OPTIMIZATION],
                relevance_score=0.8,
                summary="Summary",
                key_insights=["Insight"],
                implementation_available=True,
                discovered_at=datetime.now().isoformat()
            )
        ]

        # Filter by AGENT_SYSTEMS
        top = await mock_agent.get_top_discoveries(
            top_k=10,
            area_filter=ResearchArea.AGENT_SYSTEMS
        )

        assert len(top) == 1
        assert top[0].arxiv_id == "1"

    @pytest.mark.asyncio
    async def test_query_past_discoveries(self, mock_agent):
        """Test querying past discoveries from MemoryOS"""
        # Mock MemoryOS retrieve
        mock_memories = [
            {
                "content": "Test discovery 1",
                "type": "conversation"
            }
        ]
        mock_agent.memory.retrieve = Mock(return_value=mock_memories)

        results = await mock_agent.query_past_discoveries(
            query="agent systems",
            top_k=5
        )

        assert len(results) == 1
        assert mock_agent.memory.retrieve.called

    @pytest.mark.asyncio
    async def test_area_breakdown(self, mock_agent):
        """Test area breakdown calculation"""
        papers = [
            ResearchPaper(
                arxiv_id="1",
                title="Paper 1",
                abstract="Abstract",
                authors=["Author"],
                published_date="2025-10-23T00:00:00Z",
                source=DiscoverySource.ARXIV,
                research_areas=[ResearchArea.AGENT_SYSTEMS, ResearchArea.ORCHESTRATION],
                relevance_score=0.9,
                summary="Summary",
                key_insights=["Insight"],
                implementation_available=True,
                discovered_at=datetime.now().isoformat()
            ),
            ResearchPaper(
                arxiv_id="2",
                title="Paper 2",
                abstract="Abstract",
                authors=["Author"],
                published_date="2025-10-23T00:00:00Z",
                source=DiscoverySource.ARXIV,
                research_areas=[ResearchArea.AGENT_SYSTEMS],
                relevance_score=0.8,
                summary="Summary",
                key_insights=["Insight"],
                implementation_available=True,
                discovered_at=datetime.now().isoformat()
            )
        ]

        breakdown = mock_agent._get_area_breakdown(papers)

        assert breakdown['agent_systems'] == 2
        assert breakdown['orchestration'] == 1
        assert breakdown['llm_optimization'] == 0


class TestFactoryFunction:
    """Test factory function"""

    @pytest.mark.asyncio
    async def test_get_research_discovery_agent(self):
        """Test factory function"""
        with patch('agents.research_discovery_agent.ResearchDiscoveryAgent') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            agent = await get_research_discovery_agent()

            assert agent is mock_instance


# Integration tests (optional - requires real API keys)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_arxiv_fetch():
    """Test real arXiv API fetch (requires network)"""
    crawler = ArxivCrawler()

    papers = await crawler.fetch_recent_papers(days_back=1, max_results=5)

    assert len(papers) > 0
    assert 'arxiv_id' in papers[0]
    assert 'title' in papers[0]
    assert 'abstract' in papers[0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_discovery_cycle():
    """Test real discovery cycle (requires API keys)"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("API keys not available")

    agent = await get_research_discovery_agent()

    summary = await agent.run_discovery_cycle(
        days_back=1,
        max_papers=5,
        min_relevance_score=0.7
    )

    assert 'discovery_run_id' in summary
    assert summary['total_fetched'] > 0
