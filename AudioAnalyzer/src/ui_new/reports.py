"""
Report Generator - генерация отчётов в различных форматах.

Функционал:
- Генерация отчётов в PDF с графиками и таблицами
- Генерация отчётов в HTML для веб-публикации
- Настраиваемые шаблоны отчётов
- Краткий (summary), детальный (detailed), технический (technical) форматы

Использование:
--------------
>>> from ui_new.reports import ReportGenerator, ReportFormat
>>> 
>>> generator = ReportGenerator()
>>> report = generator.generate(results, format=ReportFormat.PDF)
"""
from __future__ import annotations

import base64
import io
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic

logger = logging.getLogger("ui_new.reports")


class ReportFormat(Enum):
    """Форматы отчётов."""
    
    PDF = auto()
    HTML = auto()
    MARKDOWN = auto()
    JSON = auto()


class ReportType(Enum):
    """Типы отчётов."""
    
    SUMMARY = "summary"        # Краткий отчёт
    DETAILED = "detailed"      # Детальный отчёт
    TECHNICAL = "technical"    # Технический отчёт


# Check for PDF support
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.debug("reportlab not installed. PDF export unavailable.")


@dataclass
class ReportSection:
    """Секция отчёта."""
    
    title: str
    content: str
    order: int = 0
    include_in_summary: bool = True
    include_in_detailed: bool = True
    include_in_technical: bool = True


@dataclass
class ReportData:
    """Данные для генерации отчёта."""
    
    title: str = "Audio Analysis Report"
    generated_at: datetime = field(default_factory=datetime.now)
    results: List[Any] = field(default_factory=list)
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Статистика
    total_files: int = 0
    total_methods: int = 0
    avg_snr: float = 0.0
    avg_lsd: float = 0.0
    total_processing_time: float = 0.0
    
    def calculate_statistics(self) -> None:
        """Вычислить статистику по результатам."""
        if not self.results:
            return
        
        self.total_files = len(set(r.source for r in self.results if hasattr(r, 'source')))
        self.total_methods = len(set(r.variant for r in self.results if hasattr(r, 'variant')))
        
        snr_values = [r.snr_db for r in self.results if hasattr(r, 'snr_db') and r.snr_db is not None]
        lsd_values = [r.lsd_db for r in self.results if hasattr(r, 'lsd_db') and r.lsd_db is not None]
        time_values = [r.time_sec for r in self.results if hasattr(r, 'time_sec') and r.time_sec is not None]
        
        if snr_values:
            self.avg_snr = sum(snr_values) / len(snr_values)
        if lsd_values:
            self.avg_lsd = sum(lsd_values) / len(lsd_values)
        if time_values:
            self.total_processing_time = sum(time_values)


class ReportTemplate:
    """Базовый шаблон отчёта."""
    
    def __init__(self, report_type: ReportType):
        self.report_type = report_type
    
    def get_sections(self, data: ReportData) -> List[ReportSection]:
        """Получить секции для данного типа отчёта."""
        return [
            section for section in data.sections
            if getattr(section, f"include_in_{self.report_type.value}", True)
        ]


class HTMLReportGenerator:
    """Генератор HTML отчётов."""
    
    def generate(self, data: ReportData, template: ReportTemplate) -> str:
        """Сгенерировать HTML отчёт."""
        data.calculate_statistics()
        
        html = self._build_html(data, template)
        return html
    
    def _build_html(self, data: ReportData, template: ReportTemplate) -> str:
        """Построить HTML документ."""
        sections = template.get_sections(data)
        
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape(data.title)}</title>
    <style>
        :root {{
            --primary: #3B82F6;
            --secondary: #64748B;
            --success: #10B981;
            --warning: #F59E0B;
            --error: #EF4444;
            --bg-color: #F8FAFC;
            --card-bg: #FFFFFF;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: linear-gradient(135deg, var(--primary), #2563EB);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        
        .header .metadata {{
            opacity: 0.9;
            font-size: 14px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .stat-card .label {{
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 5px;
        }}
        
        .stat-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: var(--primary);
        }}
        
        .section {{
            background: var(--card-bg);
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            margin: 0 0 20px 0;
            font-size: 20px;
            color: var(--text-primary);
            border-bottom: 2px solid var(--primary);
            padding-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #E2E8F0;
        }}
        
        th {{
            background-color: #F1F5F9;
            font-weight: 600;
            color: var(--text-secondary);
        }}
        
        tr:hover {{
            background-color: #F8FAFC;
        }}
        
        .method-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .method-fwht {{ background: #DBEAFE; color: #1E40AF; }}
        .method-fft {{ background: #D1FAE5; color: #065F46; }}
        .method-dct {{ background: #FEF3C7; color: #92400E; }}
        .method-dwt {{ background: #EDE9FE; color: #5B21B6; }}
        .method-huffman {{ background: #FCE7F3; color: #9D174D; }}
        .method-rosenbrock {{ background: #FEE2E2; color: #991B1B; }}
        .method-standard {{ background: #F3F4F6; color: #374151; }}
        
        .metric-good {{ color: var(--success); }}
        .metric-warning {{ color: var(--warning); }}
        .metric-error {{ color: var(--error); }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 12px;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            .section {{
                box-shadow: none;
                border: 1px solid #E2E8F0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self._escape(data.title)}</h1>
            <div class="metadata">
                Сгенерировано: {data.generated_at.strftime('%d.%m.%Y %H:%M:%S')}
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Обработано файлов</div>
                <div class="value">{data.total_files}</div>
            </div>
            <div class="stat-card">
                <div class="label">Использовано методов</div>
                <div class="value">{data.total_methods}</div>
            </div>
            <div class="stat-card">
                <div class="label">Средний SNR</div>
                <div class="value">{data.avg_snr:.1f} dB</div>
            </div>
            <div class="stat-card">
                <div class="label">Средний LSD</div>
                <div class="value">{data.avg_lsd:.3f} dB</div>
            </div>
            <div class="stat-card">
                <div class="label">Время обработки</div>
                <div class="value">{data.total_processing_time:.1f} с</div>
            </div>
        </div>
        
        {self._generate_results_table(data)}
        
        {self._generate_sections_html(sections)}
        
        <div class="footer">
            AudioAnalyzer Report Generator • {data.generated_at.year}
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_results_table(self, data: ReportData) -> str:
        """Генерировать таблицу результатов."""
        if not data.results:
            return '<div class="section"><p>Нет данных для отображения</p></div>'
        
        rows = []
        for r in data.results:
            method = getattr(r, 'variant', 'unknown')
            method_class = f"method-{method.lower()}"
            
            snr = getattr(r, 'snr_db', None)
            snr_str = f"{snr:.2f}" if snr is not None else "—"
            snr_class = ""
            if snr is not None:
                if snr > 20:
                    snr_class = "metric-good"
                elif snr > 10:
                    snr_class = "metric-warning"
                else:
                    snr_class = "metric-error"
            
            lsd = getattr(r, 'lsd_db', None)
            lsd_str = f"{lsd:.3f}" if lsd is not None else "—"
            
            time_sec = getattr(r, 'time_sec', None)
            time_str = f"{time_sec:.2f}s" if time_sec is not None else "—"
            
            size_bytes = getattr(r, 'size_bytes', 0)
            size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
            
            rows.append(f"""
            <tr>
                <td>{self._escape(getattr(r, 'source', '—'))}</td>
                <td><span class="method-badge {method_class}">{method.upper()}</span></td>
                <td>{size_mb:.3f} МБ</td>
                <td class="{snr_class}">{snr_str}</td>
                <td>{lsd_str}</td>
                <td>{time_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="section">
            <h2>📊 Результаты анализа</h2>
            <table>
                <thead>
                    <tr>
                        <th>Файл</th>
                        <th>Метод</th>
                        <th>Размер</th>
                        <th>SNR (дБ)</th>
                        <th>LSD (дБ)</th>
                        <th>Время</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
    
    def _generate_sections_html(self, sections: List[ReportSection]) -> str:
        """Генерировать дополнительные секции."""
        html_parts = []
        
        for section in sorted(sections, key=lambda s: s.order):
            html_parts.append(f"""
            <div class="section">
                <h2>{self._escape(section.title)}</h2>
                <div>{section.content}</div>
            </div>
            """)
        
        return ''.join(html_parts)
    
    def _escape(self, text: str) -> str:
        """Экранировать HTML символы."""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


class MarkdownReportGenerator:
    """Генератор Markdown отчётов."""
    
    def generate(self, data: ReportData, template: ReportTemplate) -> str:
        """Сгенерировать Markdown отчёт."""
        data.calculate_statistics()
        
        md = f"""# {data.title}

**Сгенерировано:** {data.generated_at.strftime('%d.%m.%Y %H:%M:%S')}

## 📊 Статистика

| Метрика | Значение |
|---------|----------|
| Обработано файлов | {data.total_files} |
| Использовано методов | {data.total_methods} |
| Средний SNR | {data.avg_snr:.1f} dB |
| Средний LSD | {data.avg_lsd:.3f} dB |
| Время обработки | {data.total_processing_time:.1f} с |

## 📋 Результаты анализа

| Файл | Метод | Размер | SNR (дБ) | LSD (дБ) | Время |
|------|-------|--------|----------|----------|-------|
"""
        
        for r in data.results:
            source = getattr(r, 'source', '—')
            method = getattr(r, 'variant', '—')
            size_bytes = getattr(r, 'size_bytes', 0)
            size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
            snr = getattr(r, 'snr_db', None)
            snr_str = f"{snr:.2f}" if snr is not None else "—"
            lsd = getattr(r, 'lsd_db', None)
            lsd_str = f"{lsd:.3f}" if lsd is not None else "—"
            time_sec = getattr(r, 'time_sec', None)
            time_str = f"{time_sec:.2f}s" if time_sec is not None else "—"
            
            md += f"| {source} | {method} | {size_mb:.3f} МБ | {snr_str} | {lsd_str} | {time_str} |\n"
        
        # Добавляем секции
        sections = template.get_sections(data)
        for section in sorted(sections, key=lambda s: s.order):
            md += f"\n## {section.title}\n\n{section.content}\n"
        
        md += f"\n---\n*AudioAnalyzer Report Generator • {data.generated_at.year}*\n"
        
        return md


class JSONReportGenerator:
    """Генератор JSON отчётов."""
    
    def generate(self, data: ReportData, template: ReportTemplate) -> str:
        """Сгенерировать JSON отчёт."""
        import json
        
        data.calculate_statistics()
        
        report_dict = {
            "title": data.title,
            "generated_at": data.generated_at.isoformat(),
            "statistics": {
                "total_files": data.total_files,
                "total_methods": data.total_methods,
                "avg_snr": data.avg_snr,
                "avg_lsd": data.avg_lsd,
                "total_processing_time": data.total_processing_time,
            },
            "results": [],
            "metadata": data.metadata,
        }
        
        for r in data.results:
            result_dict = {
                "source": getattr(r, 'source', None),
                "variant": getattr(r, 'variant', None),
                "size_bytes": getattr(r, 'size_bytes', None),
                "snr_db": getattr(r, 'snr_db', None),
                "lsd_db": getattr(r, 'lsd_db', None),
                "rmse": getattr(r, 'rmse', None),
                "si_sdr_db": getattr(r, 'si_sdr_db', None),
                "spec_conv": getattr(r, 'spec_conv', None),
                "spec_centroid_diff_hz": getattr(r, 'spec_centroid_diff_hz', None),
                "spec_cosine": getattr(r, 'spec_cosine', None),
                "score": getattr(r, 'score', None),
                "time_sec": getattr(r, 'time_sec', None),
                "path": getattr(r, 'path', None),
            }
            report_dict["results"].append(result_dict)
        
        return json.dumps(report_dict, indent=2, ensure_ascii=False)


class PDFReportGenerator:
    """Генератор PDF отчётов.
    
    Требует установленную библиотеку reportlab.
    """
    
    def __init__(self):
        if not HAS_REPORTLAB:
            raise ImportError(
                "reportlab не установлен. Установите: pip install reportlab"
            )
    
    def generate(self, data: ReportData, template: ReportTemplate) -> bytes:
        """Сгенерировать PDF отчёт.
        
        Returns
        -------
        bytes
            PDF содержимое в виде байтов
        """
        data.calculate_statistics()
        
        # Создаём буфер для PDF
        buffer = io.BytesIO()
        
        # Создаём документ
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        # Стили
        styles = getSampleStyleSheet()
        
        # Кастомные стили
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1E40AF'),
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1E293B'),
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
        )
        
        # Контейнер для элементов
        elements = []
        
        # Заголовок
        elements.append(Paragraph(data.title, title_style))
        elements.append(Paragraph(
            f"Сгенерировано: {data.generated_at.strftime('%d.%m.%Y %H:%M:%S')}",
            normal_style
        ))
        elements.append(Spacer(1, 20))
        
        # Статистика
        elements.append(Paragraph("📊 Статистика", heading_style))
        elements.append(Spacer(1, 10))
        
        stats_data = [
            ["Метрика", "Значение"],
            ["Обработано файлов", str(data.total_files)],
            ["Использовано методов", str(data.total_methods)],
            ["Средний SNR", f"{data.avg_snr:.1f} dB"],
            ["Средний LSD", f"{data.avg_lsd:.3f} dB"],
            ["Время обработки", f"{data.total_processing_time:.1f} с"],
        ]
        
        stats_table = Table(stats_data, colWidths=[200, 150])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 30))
        
        # Результаты
        if data.results:
            elements.append(Paragraph("📋 Результаты анализа", heading_style))
            elements.append(Spacer(1, 10))
            
            # Заголовки таблицы результатов
            results_header = ["Файл", "Метод", "SNR", "LSD", "Время"]
            results_data = [results_header]
            
            for r in data.results:
                source = getattr(r, 'source', '—')
                if len(source) > 30:
                    source = source[:27] + "..."
                    
                method = getattr(r, 'variant', '—')
                snr = getattr(r, 'snr_db', None)
                snr_str = f"{snr:.1f}" if snr is not None else "—"
                lsd = getattr(r, 'lsd_db', None)
                lsd_str = f"{lsd:.2f}" if lsd is not None else "—"
                time_sec = getattr(r, 'time_sec', None)
                time_str = f"{time_sec:.2f}s" if time_sec is not None else "—"
                
                results_data.append([source, method, snr_str, lsd_str, time_str])
            
            # Создаём таблицу (максимум 50 строк для производительности)
            if len(results_data) > 51:
                results_data = results_data[:51]
                results_data.append(["...", "...", "...", "...", "..."])
            
            results_table = Table(
                results_data,
                colWidths=[150, 80, 70, 70, 70]
            )
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E40AF')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ]))
            elements.append(results_table)
        
        # Дополнительные секции
        sections = template.get_sections(data)
        for section in sorted(sections, key=lambda s: s.order):
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(section.title, heading_style))
            elements.append(Paragraph(section.content, normal_style))
        
        # Футер
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0')))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            f"AudioAnalyzer Report Generator • {data.generated_at.year}",
            ParagraphStyle('Footer', parent=normal_style, alignment=TA_CENTER, textColor=colors.grey)
        ))
        
        # Генерируем PDF
        doc.build(elements)
        
        # Возвращаем содержимое
        buffer.seek(0)
        return buffer.getvalue()
    
    def save_to_file(self, data: ReportData, template: ReportTemplate, output_path: str) -> bool:
        """Сохранить PDF в файл."""
        try:
            pdf_bytes = self.generate(data, template)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            
            logger.info("PDF report saved to %s", output_path)
            return True
            
        except Exception as e:
            logger.error("Failed to save PDF report: %s", e)
            return False


class ReportGenerator:
    """Главный генератор отчётов.
    
    Поддерживает форматы:
    - HTML (с CSS стилизацией)
    - Markdown
    - JSON
    - PDF (требуется reportlab)
    """
    
    def __init__(self):
        self._html_generator = HTMLReportGenerator()
        self._markdown_generator = MarkdownReportGenerator()
        self._json_generator = JSONReportGenerator()
        self._pdf_generator = None
        
        if HAS_REPORTLAB:
            try:
                self._pdf_generator = PDFReportGenerator()
            except Exception as e:
                logger.warning("PDF generator init failed: %s", e)
    
    @property
    def pdf_available(self) -> bool:
        """Проверить доступность PDF генерации."""
        return self._pdf_generator is not None
    
    def generate(
        self,
        results: List[Any],
        format: ReportFormat = ReportFormat.HTML,
        report_type: ReportType = ReportType.DETAILED,
        title: str = "Audio Analysis Report",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Сгенерировать отчёт.
        
        Parameters
        ----------
        results : List[Any]
            Список результатов анализа (ResultRow)
        format : ReportFormat
            Формат отчёта
        report_type : ReportType
            Тип отчёта (summary, detailed, technical)
        title : str
            Заголовок отчёта
        metadata : Optional[Dict[str, Any]]
            Дополнительные метаданные
            
        Returns
        -------
        str | bytes
            Содержимое отчёта (строка для HTML/MD/JSON, байты для PDF)
        """
        data = ReportData(
            title=title,
            results=results,
            metadata=metadata or {},
        )
        
        template = ReportTemplate(report_type)
        
        if format == ReportFormat.HTML:
            return self._html_generator.generate(data, template)
        elif format == ReportFormat.MARKDOWN:
            return self._markdown_generator.generate(data, template)
        elif format == ReportFormat.JSON:
            return self._json_generator.generate(data, template)
        elif format == ReportFormat.PDF:
            if not self._pdf_generator:
                raise ImportError(
                    "PDF генерация недоступна. Установите: pip install reportlab"
                )
            return self._pdf_generator.generate(data, template)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def save(
        self,
        results: List[Any],
        output_path: str,
        format: Optional[ReportFormat] = None,
        **kwargs
    ) -> bool:
        """Сохранить отчёт в файл.
        
        Parameters
        ----------
        results : List[Any]
            Список результатов
        output_path : str
            Путь к файлу
        format : Optional[ReportFormat]
            Формат (определяется по расширению файла если не указан)
            
        Returns
        -------
        bool
            True при успехе
        """
        # Определяем формат по расширению
        if format is None:
            ext = Path(output_path).suffix.lower()
            format_map = {
                '.html': ReportFormat.HTML,
                '.htm': ReportFormat.HTML,
                '.md': ReportFormat.MARKDOWN,
                '.markdown': ReportFormat.MARKDOWN,
                '.json': ReportFormat.JSON,
                '.pdf': ReportFormat.PDF,
            }
            format = format_map.get(ext, ReportFormat.HTML)
        
        try:
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            if format == ReportFormat.PDF:
                # PDF требует особой обработки (бинарный формат)
                if not self._pdf_generator:
                    logger.error("PDF генерация недоступна. Установите: pip install reportlab")
                    return False
                
                data = ReportData(
                    title=kwargs.get('title', "Audio Analysis Report"),
                    results=results,
                    metadata=kwargs.get('metadata', {}),
                )
                data.calculate_statistics()
                
                report_type = ReportType(kwargs.get('report_type', 'detailed'))
                template = ReportTemplate(report_type)
                
                return self._pdf_generator.save_to_file(data, template, output_path)
            else:
                # Текстовые форматы
                content = self.generate(results, format=format, **kwargs)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            logger.info("Report saved to %s", output_path)
            return True
            
        except Exception as e:
            logger.error("Failed to save report: %s", e)
            return False
    
    def generate_summary(self, results: List[Any]) -> str:
        """Сгенерировать краткий отчёт."""
        return self.generate(
            results,
            format=ReportFormat.HTML,
            report_type=ReportType.SUMMARY
        )
    
    def generate_detailed(self, results: List[Any]) -> str:
        """Сгенерировать детальный отчёт."""
        return self.generate(
            results,
            format=ReportFormat.HTML,
            report_type=ReportType.DETAILED
        )
    
    def generate_technical(self, results: List[Any]) -> str:
        """Сгенерировать технический отчёт."""
        return self.generate(
            results,
            format=ReportFormat.JSON,
            report_type=ReportType.TECHNICAL
        )
    
    def generate_pdf(self, results: List[Any], **kwargs) -> bytes:
        """Сгенерировать PDF отчёт.
        
        Raises
        ------
        ImportError
            Если reportlab не установлен
            
        Returns
        -------
        bytes
            PDF содержимое
        """
        return self.generate(
            results,
            format=ReportFormat.PDF,
            **kwargs
        )
    
    def save_pdf(
        self,
        results: List[Any],
        output_path: str,
        **kwargs
    ) -> bool:
        """Сохранить PDF отчёт в файл.
        
        Parameters
        ----------
        results : List[Any]
            Список результатов
        output_path : str
            Путь к файлу (.pdf)
            
        Returns
        -------
        bool
            True при успехе
        """
        return self.save(
            results,
            output_path,
            format=ReportFormat.PDF,
            **kwargs
        )
    
    @staticmethod
    def is_pdf_available() -> bool:
        """Проверить доступность PDF генерации."""
        return HAS_REPORTLAB


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    "ReportGenerator",
    "ReportFormat",
    "ReportType",
    "ReportData",
    "ReportSection",
    "HAS_REPORTLAB",
]
