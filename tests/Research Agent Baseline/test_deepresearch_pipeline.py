from __future__ import annotations

import json
from pathlib import Path

from pipelines.deepresearch import DeepResearchConfig, DeepResearchPipeline
from pipelines.deepresearch.providers import ResearchPrompt, ResearchProvider, ResearchExample


class RecordingProvider(ResearchProvider):
    def __init__(self) -> None:
        self.calls: list[tuple[ResearchPrompt, int]] = []

    def generate_examples(self, prompt: ResearchPrompt, batch_size: int):
        self.calls.append((prompt, batch_size))
        return [
            ResearchExample(
                agent=prompt.agent,
                topic=prompt.topic,
                query=f"query for {prompt.topic}",
                findings=["alpha", "beta"],
                reasoning_trace=["step1", "step2"],
                citations=["https://example.com"],
            )
        ]


def test_pipeline_generates_dataset(tmp_path: Path):
    config = DeepResearchConfig(
        output_dir=tmp_path / "output",
        prompts_dir=tmp_path / "prompts",
        target_example_count=3,
        agents=["qa_agent"],
    )
    config.ensure_directories()
    prompt_file = config.prompts_dir / "qa_agent.json"
    prompt_file.write_text(
        json.dumps(
            [
                {
                    "topic": "login regression",
                    "instructions": "Investigate login issue",
                }
            ]
        )
    )

    provider = RecordingProvider()
    pipeline = DeepResearchPipeline(config, provider=provider)
    output_path = pipeline.run(batch_size=1, max_examples=1)

    assert output_path.exists()
    with output_path.open() as handle:
        lines = [json.loads(line) for line in handle]

    assert len(lines) == 1
    assert lines[0]["agent"] == "qa_agent"
    assert lines[0]["topic"] == "login regression"
    assert provider.calls, "provider should have been invoked"


def test_pipeline_uses_default_prompts_when_missing(tmp_path: Path):
    config = DeepResearchConfig(
        output_dir=tmp_path / "output",
        prompts_dir=tmp_path / "missing",
        target_example_count=5,
        agents=["qa_agent", "support_agent"],
    )
    provider = RecordingProvider()
    pipeline = DeepResearchPipeline(config, provider=provider)

    output_path = pipeline.run(batch_size=1, max_examples=2)
    assert output_path.exists()
    assert len(provider.calls) == 2
