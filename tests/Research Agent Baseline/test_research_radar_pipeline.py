from __future__ import annotations

from datetime import datetime

from infrastructure.research_radar.clusterer import ResearchRadarClusterer
from infrastructure.research_radar.crawler import ResearchRadarCrawler
from infrastructure.research_radar.dashboard import ResearchRadarDashboard
from infrastructure.research_radar.embedder import ResearchRadarEmbedder
from infrastructure.research_radar.settings import ResearchRadarSettings, SourceConfig


class _DummySentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def encode(self, texts, convert_to_numpy=False):  # noqa: ANN001 - third-party signature
        base = float(len(texts))
        return [[base + idx, 0.5] for idx, _ in enumerate(texts)]


def test_research_radar_pipeline(monkeypatch, tmp_path):
    run_at = datetime(2025, 10, 30, 9, 0, 0)
    run_folder = run_at.strftime("%Y%m%d")

    settings = ResearchRadarSettings(
        root=tmp_path,
        raw_dir=tmp_path / "raw",
        embeddings_dir=tmp_path / "embeddings",
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        cache_dir=tmp_path / "cache",
        dashboard_path=tmp_path / "reports" / "dashboard.html",
        sources=[SourceConfig(name="stub", type="api", url="https://example.com")],
    )

    stub_records = [
        {
            "id": f"stub-{idx}",
            "title": f"Agent Research Item {idx}",
            "summary": "Explores multi-agent collaboration techniques.",
            "url": f"https://example.com/paper-{idx}",
            "published_at": "2025-10-28T00:00:00Z",
            "source": "stub",
            "tags": ["multi-agent", "orchestration"],
        }
        for idx in range(3)
    ]

    monkeypatch.setattr(
        ResearchRadarCrawler,
        "_fetch_source",
        lambda self, source, timestamp: list(stub_records),
    )

    monkeypatch.setattr(
        "infrastructure.research_radar.embedder.SentenceTransformer",
        _DummySentenceTransformer,
    )

    crawler = ResearchRadarCrawler(settings)
    crawler.run(run_datetime=run_at)

    embedder = ResearchRadarEmbedder(settings)
    embedded = embedder.run(date_folder=run_folder)
    assert embedded, "Expected embedded records to be generated"

    clusterer = ResearchRadarClusterer(settings)
    cluster_output = clusterer.run(date_folder=run_folder)
    assert cluster_output["trends"], "Expected at least one trend in cluster output"

    dashboard = ResearchRadarDashboard(settings)
    markdown_path = dashboard.run(date_folder=run_folder)

    assert markdown_path.exists()
    assert settings.dashboard_path.exists()
    content = markdown_path.read_text(encoding="utf-8")
    assert "Genesis Research Radar" in content
    assert "Top Trends" in content
