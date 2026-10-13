import pytest
from fastapi.testclient import TestClient
from legal_rag.api.main import app, CORPUS_STORE
from legal_rag.schemas import ArticleRecord

@pytest.fixture(autouse=True)
def setup_corpus():
    CORPUS_STORE[147] = ArticleRecord(
        article_number=147,
        book="Obligations",
        chapter="Contracts",
        section="Effects",
        topic="General",
        text_ar="العقد شريعة المتعاقدين، فلا يجوز نقضه ولا تعديله.",
        text_en="The contract makes the law of the parties.",
        is_repealed=False,
        source_page=34,
        citation="Egyptian Civil Code, Article 147"
    )
    yield
    CORPUS_STORE.clear()

def test_api_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_metadata():
    client = TestClient(app)
    response = client.get("/metadata")
    assert response.status_code == 200
    assert response.json()["total_articles"] == 1

def test_api_ask_valid():
    client = TestClient(app)
    response = client.post("/ask", json={"question": "ما هو العقد؟", "top_k": 1})
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "Egyptian Civil Code, Article 147" in data["sources"]
    assert "X-Request-ID" in response.headers

def test_api_ask_validation_error():
    client = TestClient(app)
    # Empty question triggers 422
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422
    assert "detail" in response.json()
    
def test_api_health_unhealthy():
    CORPUS_STORE.clear()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"