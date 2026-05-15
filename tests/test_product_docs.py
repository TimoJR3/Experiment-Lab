"""Тесты русской документации для Product Analyst подачи."""

from pathlib import Path

from app.db.prepare_demo import DEMO_EXPERIMENT_KEY

BASE_DIR = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    """Прочитать текстовый файл репозитория как UTF-8."""
    return (BASE_DIR / path).read_text(encoding="utf-8")


def test_readme_contains_product_analyst_sections() -> None:
    """README должен понятно объяснять проект на русском языке."""
    readme = _read("README.md")

    required_sections = [
        "## Бизнес-задача",
        "## Продуктовые метрики",
        "## Дизайн эксперимента",
        "## Статистическая интерпретация",
        "## Демо-сценарий",
        "## Схема данных",
        "## Ограничения",
        "## Что демонстрирует проект",
    ]

    for section in required_sections:
        assert section in readme


def test_readme_mentions_supported_metrics() -> None:
    """README должен перечислять метрики, которые реализованы в коде."""
    readme = _read("README.md")

    for metric in [
        "conversion_rate",
        "average_revenue_per_user",
        "average_order_value",
        "purchase_rate",
        "p_value",
        "confidence_interval",
    ]:
        assert metric in readme


def test_github_presentation_is_documented() -> None:
    """README должен содержать описание и темы для GitHub."""
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
        "лаборатория",
        "A/B-тестирования",
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
