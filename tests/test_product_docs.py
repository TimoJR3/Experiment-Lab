"""Тесты русской документации для Product/Data Analyst подачи."""

from __future__ import annotations

import re
from pathlib import Path

from app.db.prepare_demo import DEMO_EXPERIMENT_KEY

BASE_DIR = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    """Прочитать текстовый файл репозитория как UTF-8."""
    return (BASE_DIR / path).read_text(encoding="utf-8")


def test_readme_contains_cis_portfolio_sections() -> None:
    """README должен соответствовать структуре портфолио для СНГ-рынка."""
    readme = _read("README.md")

    required_sections = [
        "## Обзор проекта",
        "## Контекст эксперимента",
        "## Пример гипотезы",
        "## Дизайн эксперимента",
        "## Метрики",
        "## Статистические методы",
        "## Архитектура проекта",
        "## API endpoints",
        "## Dashboard и скриншоты",
        "## Как запустить локально",
        "## Примеры API-запросов",
        "## Структура репозитория",
        "## Ограничения",
        "## Что можно улучшить",
        "## Формулировки для резюме",
        "## Рассказ о проекте для интервью",
    ]

    for section in required_sections:
        assert section in readme


def test_readme_mentions_supported_metrics_and_statistics() -> None:
    """README должен перечислять метрики и статистические поля из проекта."""
    readme = _read("README.md")

    for term in [
        "conversion_rate",
        "average_revenue_per_user",
        "average_order_value",
        "purchase_rate",
        "ARPU",
        "AOV",
        "uplift",
        "p_value",
        "confidence_interval",
        "statistically significant",
    ]:
        assert term in readme


def test_readme_documents_real_api_endpoints() -> None:
    """README должен документировать существующие FastAPI endpoints."""
    readme = _read("README.md")

    for endpoint in [
        "/health",
        "/experiments",
        "/experiments/{id}",
        "/experiments/{id}/assignments",
        "/experiments/{id}/metrics",
        "/experiments/{id}/results",
        "/users/summary",
        "/events/summary",
        "/experiments/{experiment_key}/start",
        "/experiments/{experiment_key}/analyze",
    ]:
        assert endpoint in readme


def test_readme_embeds_existing_screenshots() -> None:
    """Все screenshots из README должны существовать в репозитории."""
    readme = _read("README.md")
    image_paths = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)

    assert image_paths == [
        "docs/assets/screenshots/01_dashboard_overview.png",
        "docs/assets/screenshots/02_events_and_experiments.png",
        "docs/assets/screenshots/03_selected_experiment.png",
        "docs/assets/screenshots/04_metrics.png",
        "docs/assets/screenshots/05_statistical_results.png",
    ]
    for image_path in image_paths:
        assert (BASE_DIR / image_path).is_file()


def test_readme_contains_resume_and_interview_materials() -> None:
    """README должен содержать материалы для резюме и интервью."""
    readme = _read("README.md")

    assert "### Product Analyst Intern" in readme
    assert "### Data Analyst Intern" in readme
    assert "### 60-секундный рассказ" in readme
    assert "### 10 вопросов и ответов для интервью" in readme
    assert readme.count("**") >= 20


def test_github_presentation_is_documented() -> None:
    """README должен содержать описание и topics для GitHub."""
    readme = _read("README.md")

    assert (
        "Демонстрационный проект по A/B-тестированию с расчётом "
        "продуктовых метрик, статистической интерпретацией, FastAPI, "
        "PostgreSQL и Streamlit."
    ) in readme
    for topic in [
        "product-analytics",
        "ab-testing",
        "python",
        "fastapi",
        "postgresql",
        "streamlit",
        "statistics",
        "uplift",
        "confidence-intervals",
    ]:
        assert topic in readme


def test_product_case_and_interview_notes_reference_demo_key() -> None:
    """Документация должна ссылаться на воспроизводимый demo-эксперимент."""
    product_case = _read("docs/product_case.md")
    interview_notes = _read("docs/interview_notes.md")

    assert DEMO_EXPERIMENT_KEY in product_case
    assert DEMO_EXPERIMENT_KEY in interview_notes


def test_product_docs_are_russian_and_honest() -> None:
    """Документация должна использовать честное позиционирование без завышений."""
    docs = "\n".join(
        [
            _read("README.md"),
            _read("docs/product_case.md"),
            _read("docs/interview_notes.md"),
        ]
    )
    normalized_docs = docs.lower()

    for required_phrase in [
        "демонстрационный проект",
        "A/B",
        "Product Analyst",
        "Data Analyst",
        "synthetic",
    ]:
        assert required_phrase.lower() in normalized_docs

    forbidden_phrases = [
        "production-ready",
        "enterprise-level",
        "боевая система",
        "промышленная платформа",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in docs


def test_readme_documents_demo_command() -> None:
    """README должен описывать команду подготовки demo-данных."""
    readme = _read("README.md")

    assert "docker compose up --build -d" in readme
    assert "docker compose exec api python -m app.db.prepare_demo" in readme
    assert "http://localhost:8501" in readme
    assert "http://localhost:8000/docs" in readme
