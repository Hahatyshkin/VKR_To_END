"""
Tests for Report Generator.

Tests verify:
- ReportFormat and ReportType enums
- ReportData calculations
- HTML report generation
- Markdown report generation
- JSON report generation
- ReportGenerator save functionality
"""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestReportFormat:
    """Tests for ReportFormat enum."""
    
    def test_format_values(self):
        """Test that all format values are defined."""
        from ui_new.reports import ReportFormat
        
        assert ReportFormat.HTML
        assert ReportFormat.MARKDOWN
        assert ReportFormat.JSON
    
    def test_format_unique(self):
        """Test that all formats are unique."""
        from ui_new.reports import ReportFormat
        
        values = [f.value for f in ReportFormat]
        assert len(values) == len(set(values))


class TestReportType:
    """Tests for ReportType enum."""
    
    def test_type_values(self):
        """Test that all type values are defined."""
        from ui_new.reports import ReportType
        
        assert ReportType.SUMMARY
        assert ReportType.DETAILED
        assert ReportType.TECHNICAL


class TestReportData:
    """Tests for ReportData."""
    
    def test_default_values(self):
        """Test default data values."""
        from ui_new.reports import ReportData
        
        data = ReportData()
        
        assert data.title == "Audio Analysis Report"
        assert data.total_files == 0
        assert data.total_methods == 0
        assert data.avg_snr == 0.0
        assert data.avg_lsd == 0.0
    
    def test_calculate_statistics(self):
        """Test statistics calculation."""
        from ui_new.reports import ReportData
        
        # Create mock results
        class MockResult:
            def __init__(self, source, variant, snr_db, lsd_db, time_sec):
                self.source = source
                self.variant = variant
                self.snr_db = snr_db
                self.lsd_db = lsd_db
                self.time_sec = time_sec
        
        results = [
            MockResult("file1.wav", "fwht", 20.0, 1.5, 1.0),
            MockResult("file1.wav", "fft", 18.0, 1.8, 0.8),
            MockResult("file2.wav", "fwht", 22.0, 1.2, 1.2),
        ]
        
        data = ReportData(results=results)
        data.calculate_statistics()
        
        assert data.total_files == 2  # file1.wav and file2.wav
        assert data.total_methods == 2  # fwht and fft
        assert data.avg_snr == pytest.approx(20.0, rel=0.1)
        assert data.avg_lsd == pytest.approx(1.5, rel=0.1)


class TestHTMLReportGenerator:
    """Tests for HTML report generation."""
    
    def test_generate_empty(self):
        """Test generating report with no results."""
        from ui_new.reports import (
            HTMLReportGenerator, ReportData, ReportTemplate, ReportType
        )
        
        generator = HTMLReportGenerator()
        data = ReportData()
        template = ReportTemplate(ReportType.DETAILED)
        
        html = generator.generate(data, template)
        
        assert "<!DOCTYPE html>" in html
        assert "Audio Analysis Report" in html
    
    def test_generate_with_results(self):
        """Test generating report with results."""
        from ui_new.reports import (
            HTMLReportGenerator, ReportData, ReportTemplate, ReportType
        )
        
        class MockResult:
            def __init__(self):
                self.source = "test.wav"
                self.variant = "fwht"
                self.snr_db = 20.0
                self.lsd_db = 1.5
                self.time_sec = 1.0
                self.size_bytes = 1024 * 1024
        
        generator = HTMLReportGenerator()
        data = ReportData(results=[MockResult()])
        data.calculate_statistics()
        template = ReportTemplate(ReportType.DETAILED)
        
        html = generator.generate(data, template)
        
        assert "test.wav" in html
        assert "FWHT" in html
        assert "20.0" in html


class TestMarkdownReportGenerator:
    """Tests for Markdown report generation."""
    
    def test_generate_empty(self):
        """Test generating markdown with no results."""
        from ui_new.reports import (
            MarkdownReportGenerator, ReportData, ReportTemplate, ReportType
        )
        
        generator = MarkdownReportGenerator()
        data = ReportData()
        template = ReportTemplate(ReportType.DETAILED)
        
        md = generator.generate(data, template)
        
        assert "# Audio Analysis Report" in md
        assert "## 📊 Статистика" in md
    
    def test_generate_with_results(self):
        """Test generating markdown with results."""
        from ui_new.reports import (
            MarkdownReportGenerator, ReportData, ReportTemplate, ReportType
        )
        
        class MockResult:
            def __init__(self):
                self.source = "test.wav"
                self.variant = "fft"
                self.snr_db = 18.5
                self.lsd_db = 2.0
                self.time_sec = 0.5
                self.size_bytes = 512 * 1024
        
        generator = MarkdownReportGenerator()
        data = ReportData(results=[MockResult()])
        data.calculate_statistics()
        template = ReportTemplate(ReportType.DETAILED)
        
        md = generator.generate(data, template)
        
        assert "test.wav" in md
        assert "fft" in md


class TestJSONReportGenerator:
    """Tests for JSON report generation."""
    
    def test_generate_empty(self):
        """Test generating JSON with no results."""
        from ui_new.reports import (
            JSONReportGenerator, ReportData, ReportTemplate, ReportType
        )
        
        generator = JSONReportGenerator()
        data = ReportData()
        template = ReportTemplate(ReportType.TECHNICAL)
        
        json_str = generator.generate(data, template)
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        
        assert parsed["title"] == "Audio Analysis Report"
        assert "statistics" in parsed
        assert "results" in parsed
    
    def test_generate_with_results(self):
        """Test generating JSON with results."""
        from ui_new.reports import (
            JSONReportGenerator, ReportData, ReportTemplate, ReportType
        )
        
        class MockResult:
            def __init__(self):
                self.source = "test.wav"
                self.variant = "dct"
                self.snr_db = 15.0
                self.lsd_db = 2.5
                self.time_sec = 0.3
                self.size_bytes = 256 * 1024
        
        generator = JSONReportGenerator()
        data = ReportData(results=[MockResult()])
        data.calculate_statistics()
        template = ReportTemplate(ReportType.TECHNICAL)
        
        json_str = generator.generate(data, template)
        
        parsed = json.loads(json_str)
        
        assert len(parsed["results"]) == 1
        assert parsed["results"][0]["source"] == "test.wav"


class TestReportGenerator:
    """Tests for main ReportGenerator class."""
    
    def test_create_generator(self):
        """Test creating generator instance."""
        from ui_new.reports import ReportGenerator
        
        generator = ReportGenerator()
        
        assert generator is not None
    
    def test_generate_html(self):
        """Test generating HTML report."""
        from ui_new.reports import ReportGenerator, ReportFormat
        
        generator = ReportGenerator()
        
        html = generator.generate([], format=ReportFormat.HTML)
        
        assert "<!DOCTYPE html>" in html
    
    def test_generate_markdown(self):
        """Test generating Markdown report."""
        from ui_new.reports import ReportGenerator, ReportFormat
        
        generator = ReportGenerator()
        
        md = generator.generate([], format=ReportFormat.MARKDOWN)
        
        assert "# Audio Analysis Report" in md
    
    def test_generate_json(self):
        """Test generating JSON report."""
        from ui_new.reports import ReportGenerator, ReportFormat
        
        generator = ReportGenerator()
        
        json_str = generator.generate([], format=ReportFormat.JSON)
        
        parsed = json.loads(json_str)
        assert "title" in parsed
    
    def test_save_to_file(self):
        """Test saving report to file."""
        from ui_new.reports import ReportGenerator, ReportFormat
        
        generator = ReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            
            result = generator.save([], str(output_path), format=ReportFormat.HTML)
            
            assert result is True
            assert output_path.exists()
    
    def test_save_markdown(self):
        """Test saving Markdown report."""
        from ui_new.reports import ReportGenerator
        
        generator = ReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            
            result = generator.save([], str(output_path))
            
            assert result is True
            assert output_path.exists()
    
    def test_generate_summary(self):
        """Test generating summary report."""
        from ui_new.reports import ReportGenerator
        
        generator = ReportGenerator()
        
        html = generator.generate_summary([])
        
        assert "<!DOCTYPE html>" in html
    
    def test_generate_detailed(self):
        """Test generating detailed report."""
        from ui_new.reports import ReportGenerator
        
        generator = ReportGenerator()
        
        html = generator.generate_detailed([])
        
        assert "<!DOCTYPE html>" in html


class TestExports:
    """Tests for module exports."""
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        from ui_new.reports import __all__
        
        expected = [
            "ReportGenerator",
            "ReportFormat",
            "ReportType",
            "ReportData",
            "ReportSection",
        ]
        
        for export in expected:
            assert export in __all__
