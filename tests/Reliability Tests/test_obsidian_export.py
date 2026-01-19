#!/usr/bin/env python3
"""
Tests for Obsidian Documentation Export System

Tests cover:
- Markdown file parsing and categorization
- Link transformation (relative → wikilinks)
- Frontmatter extraction and standardization
- Image copying and path transformation
- Export completeness
- Knowledge graph generation
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from export_docs_obsidian import (
    ObsidianExporter,
    MarkdownFile,
    ExportReport
)
from generate_knowledge_graph import (
    KnowledgeGraphGenerator,
    GraphNode,
    GraphEdge,
    GraphStats
)


@pytest.fixture
def temp_vault():
    """Create temporary vault directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_source():
    """Create temporary source directory with test files"""
    temp_dir = tempfile.mkdtemp()
    source_path = Path(temp_dir)

    # Create test markdown files
    (source_path / 'docs').mkdir()
    (source_path / 'tests').mkdir()

    # Core file
    with open(source_path / 'README.md', 'w') as f:
        f.write("""---
title: Genesis README
---

# Genesis Project

This is the main README.

See [[PROJECT_STATUS]] for current status.
""")

    # Architecture file
    with open(source_path / 'docs' / 'ARCHITECTURE.md', 'w') as f:
        f.write("""---
title: System Architecture
tags: [architecture, design]
category: Architecture
---

# System Architecture

Overview of the system.

Related: [[IMPLEMENTATION_GUIDE]]

![Architecture Diagram](./diagrams/arch.png)
""")

    # Test file
    with open(source_path / 'tests' / 'TEST_GUIDE.md', 'w') as f:
        f.write("""---
title: Testing Guide
tags: [testing]
---

# Testing Guide

How to run tests.

Standard link: [Architecture](../docs/ARCHITECTURE.md)
""")

    # Create test image
    (source_path / 'docs' / 'diagrams').mkdir()
    with open(source_path / 'docs' / 'diagrams' / 'arch.png', 'wb') as f:
        f.write(b'fake_image_data')

    yield source_path
    shutil.rmtree(temp_dir)


class TestObsidianExporter:
    """Test cases for ObsidianExporter"""

    @pytest.mark.asyncio
    async def test_scan_documentation(self, temp_source, temp_vault):
        """Test scanning markdown files"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()

        assert len(files) == 3  # README, ARCHITECTURE, TEST_GUIDE
        assert all(isinstance(f, MarkdownFile) for f in files)

        # Check that files were cached
        assert len(exporter.file_cache) == 3

    @pytest.mark.asyncio
    async def test_categorize_core_file(self, temp_source, temp_vault):
        """Test categorization of core files"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        readme = next(f for f in files if 'README' in f.source_path)

        assert readme.category == 'Core'
        assert readme.is_public is True

    @pytest.mark.asyncio
    async def test_categorize_architecture_file(self, temp_source, temp_vault):
        """Test categorization of architecture files"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        arch = next(f for f in files if 'ARCHITECTURE' in f.source_path)

        assert arch.category == 'Architecture'
        assert arch.is_public is True

    @pytest.mark.asyncio
    async def test_categorize_test_file(self, temp_source, temp_vault):
        """Test categorization of test files"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        test = next(f for f in files if 'TEST_GUIDE' in f.source_path)

        assert test.category == 'Testing'

    @pytest.mark.asyncio
    async def test_extract_frontmatter(self, temp_source, temp_vault):
        """Test frontmatter extraction"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        arch = next(f for f in files if 'ARCHITECTURE' in f.source_path)

        assert 'title' in arch.frontmatter
        assert arch.frontmatter['title'] == 'System Architecture'
        assert 'tags' in arch.frontmatter
        assert 'architecture' in arch.frontmatter['tags']

    @pytest.mark.asyncio
    async def test_extract_title_from_frontmatter(self, temp_source, temp_vault):
        """Test title extraction from frontmatter"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        arch = next(f for f in files if 'ARCHITECTURE' in f.source_path)

        assert arch.title == 'System Architecture'

    @pytest.mark.asyncio
    async def test_extract_title_from_heading(self, temp_source, temp_vault):
        """Test title extraction from H1 when no frontmatter"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        # Create file without title in frontmatter
        test_file = temp_source / 'NO_TITLE.md'
        with open(test_file, 'w') as f:
            f.write("# This Is The Title\n\nContent here.")

        files = await exporter.scan_documentation()
        no_title = next(f for f in files if 'NO_TITLE' in f.source_path)

        assert no_title.title == 'This Is The Title'

    @pytest.mark.asyncio
    async def test_extract_links(self, temp_source, temp_vault):
        """Test link extraction from markdown"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        readme = next(f for f in files if 'README' in f.source_path)

        assert 'PROJECT_STATUS' in readme.links

    @pytest.mark.asyncio
    async def test_extract_tags(self, temp_source, temp_vault):
        """Test tag extraction"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        arch = next(f for f in files if 'ARCHITECTURE' in f.source_path)

        assert 'architecture' in arch.tags
        assert 'design' in arch.tags

    @pytest.mark.asyncio
    async def test_transform_wikilink(self, temp_source, temp_vault):
        """Test wikilink transformation"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        readme = next(f for f in files if 'README' in f.source_path)

        transformed = await exporter.transform_markdown(readme)

        # Wikilinks should remain unchanged
        assert '[[PROJECT_STATUS]]' in transformed

    @pytest.mark.asyncio
    async def test_transform_markdown_link_to_wikilink(self, temp_source, temp_vault):
        """Test transformation of markdown links to wikilinks"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        test = next(f for f in files if 'TEST_GUIDE' in f.source_path)

        transformed = await exporter.transform_markdown(test)

        # Markdown link should be transformed to wikilink
        assert '[[ARCHITECTURE|Architecture]]' in transformed

    @pytest.mark.asyncio
    async def test_transform_image_path(self, temp_source, temp_vault):
        """Test image path transformation"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        arch = next(f for f in files if 'ARCHITECTURE' in f.source_path)

        transformed = await exporter.transform_markdown(arch)

        # Image path should be transformed to _attachments
        assert '_attachments/' in transformed
        assert 'arch' in transformed

    @pytest.mark.asyncio
    async def test_copy_image(self, temp_source, temp_vault):
        """Test image file copying"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        await exporter.export_to_obsidian()

        # Check that attachments directory was created
        attachments_dir = temp_vault / '_attachments'
        assert attachments_dir.exists()

        # Check that image was copied
        images = list(attachments_dir.glob('*.png'))
        assert len(images) > 0
        assert exporter.report.images_copied > 0

    @pytest.mark.asyncio
    async def test_export_creates_categories(self, temp_source, temp_vault):
        """Test that export creates category directories"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        await exporter.export_to_obsidian()

        # Check category directories
        assert (temp_vault / 'Core').exists()
        assert (temp_vault / 'Architecture').exists()
        assert (temp_vault / 'Testing').exists()

    @pytest.mark.asyncio
    async def test_export_preserves_filename(self, temp_source, temp_vault):
        """Test that export preserves original filenames"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        await exporter.export_to_obsidian()

        assert (temp_vault / 'Core' / 'README.md').exists()
        assert (temp_vault / 'Architecture' / 'ARCHITECTURE.md').exists()

    @pytest.mark.asyncio
    async def test_export_adds_frontmatter(self, temp_source, temp_vault):
        """Test that export adds required frontmatter"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        await exporter.export_to_obsidian()

        # Read exported file
        with open(temp_vault / 'Core' / 'README.md', 'r') as f:
            content = f.read()

        # Check frontmatter
        assert 'dg-publish: true' in content
        assert 'publish: true' in content
        assert 'category: Core' in content

    @pytest.mark.asyncio
    async def test_export_report_statistics(self, temp_source, temp_vault):
        """Test export report statistics"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        report = await exporter.export_to_obsidian()

        assert report.total_files_scanned == 3
        assert report.files_exported == 3
        assert report.files_skipped == 0
        assert report.links_transformed > 0
        assert len(report.categories) > 0

    @pytest.mark.asyncio
    async def test_generate_index_pages(self, temp_source, temp_vault):
        """Test index page generation"""
        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        await exporter.export_to_obsidian()
        await exporter.generate_index_pages()

        # Check index files
        assert (temp_vault / 'Core' / 'INDEX.md').exists()
        assert (temp_vault / 'Architecture' / 'INDEX.md').exists()

        # Read index content
        with open(temp_vault / 'Architecture' / 'INDEX.md', 'r') as f:
            content = f.read()

        assert 'Architecture Documentation' in content
        assert '[[ARCHITECTURE' in content

    @pytest.mark.asyncio
    async def test_skip_external_links(self, temp_source, temp_vault):
        """Test that external links are not transformed"""
        # Create file with external link
        with open(temp_source / 'EXTERNAL.md', 'w') as f:
            f.write("[Google](https://google.com)\n")

        exporter = ObsidianExporter(str(temp_source), str(temp_vault))

        files = await exporter.scan_documentation()
        ext_file = next(f for f in files if 'EXTERNAL' in f.source_path)

        transformed = await exporter.transform_markdown(ext_file)

        # External link should remain unchanged
        assert 'https://google.com' in transformed
        assert '[[google.com' not in transformed


class TestKnowledgeGraphGenerator:
    """Test cases for KnowledgeGraphGenerator"""

    @pytest.mark.asyncio
    async def test_scan_vault(self, temp_vault):
        """Test vault scanning"""
        # Create test files
        (temp_vault / 'Core').mkdir()
        with open(temp_vault / 'Core' / 'README.md', 'w') as f:
            f.write("# README\n\nContent")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        files = await generator._scan_vault()

        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_parse_file_creates_node(self, temp_vault):
        """Test that parsing creates graph node"""
        # Create test file
        test_file = temp_vault / 'TEST.md'
        with open(test_file, 'w') as f:
            f.write("""---
title: Test Document
tags: [test]
---

# Test Document

Content with [[LINK]]
""")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator._parse_file(test_file)

        assert 'TEST' in generator.nodes
        node = generator.nodes['TEST']
        assert node.title == 'Test Document'
        assert 'test' in node.tags
        assert 'LINK' in node.links

    @pytest.mark.asyncio
    async def test_build_graph(self, temp_vault):
        """Test complete graph building"""
        # Create test files
        with open(temp_vault / 'A.md', 'w') as f:
            f.write("---\ntitle: A\n---\n# A\n\n[[B]]")

        with open(temp_vault / 'B.md', 'w') as f:
            f.write("---\ntitle: B\n---\n# B\n\n[[A]]")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator.build_graph()

        assert len(generator.nodes) == 2
        assert len(generator.edges) > 0

    @pytest.mark.asyncio
    async def test_calculate_backlinks(self, temp_vault):
        """Test backlink calculation"""
        # Create test files
        with open(temp_vault / 'SOURCE.md', 'w') as f:
            f.write("# Source\n\n[[TARGET]]")

        with open(temp_vault / 'TARGET.md', 'w') as f:
            f.write("# Target\n\nContent")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator.build_graph()

        target_node = generator.nodes['TARGET']
        assert 'SOURCE' in target_node.backlinks

    @pytest.mark.asyncio
    async def test_generate_stats(self, temp_vault):
        """Test statistics generation"""
        # Create test files
        with open(temp_vault / 'A.md', 'w') as f:
            f.write("---\ntags: [tag1]\n---\n# A\n\n[[B]]")

        with open(temp_vault / 'B.md', 'w') as f:
            f.write("---\ntags: [tag1]\n---\n# B")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator.build_graph()
        stats = await generator.generate_stats()

        assert stats.total_nodes == 2
        assert len(stats.top_tags) > 0

    @pytest.mark.asyncio
    async def test_export_graph_data(self, temp_vault):
        """Test graph data export"""
        # Create test file
        with open(temp_vault / 'TEST.md', 'w') as f:
            f.write("# Test")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator.build_graph()

        output_path = temp_vault / 'graph_data.json'
        await generator.export_graph_data(output_path)

        assert output_path.exists()

        # Verify JSON structure
        import json
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert 'nodes' in data
        assert 'edges' in data
        assert 'metadata' in data

    @pytest.mark.asyncio
    async def test_generate_main_moc(self, temp_vault):
        """Test main MOC generation"""
        # Create test files
        with open(temp_vault / 'A.md', 'w') as f:
            f.write("---\ncategory: Core\n---\n# A")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator.build_graph()
        await generator.generate_moc_files(temp_vault)

        moc_path = temp_vault / 'MOC_Main.md'
        assert moc_path.exists()

        with open(moc_path, 'r') as f:
            content = f.read()

        assert 'Genesis Knowledge Base' in content

    @pytest.mark.asyncio
    async def test_generate_category_mocs(self, temp_vault):
        """Test category MOC generation"""
        # Create test files
        (temp_vault / 'Core').mkdir()
        with open(temp_vault / 'Core' / 'A.md', 'w') as f:
            f.write("---\ncategory: Core\n---\n# A")

        generator = KnowledgeGraphGenerator(str(temp_vault))
        await generator.build_graph()
        await generator.generate_moc_files(temp_vault)

        moc_path = temp_vault / 'Core' / 'MOC.md'
        assert moc_path.exists()

        with open(moc_path, 'r') as f:
            content = f.read()

        assert 'Core Map of Content' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
