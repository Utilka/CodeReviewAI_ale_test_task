# tests/test_main.py

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.github_fetcher import Repository
from app.openAI_reviewer import Review

# Set up FastAPI test client
client = TestClient(app)


# main.py Tests

test_repo_code = """
--- folder1/test1.py ---
print("Hello World from test directory!")

--- test.py ---
print("Hello World!")

"""
test_responce = {
    "Found files": [
        "folder1/test1.py",
        "test.py",
    ],
    "Downsides/Comments": "Mocked Downsides",
    "Rating": "Mocked Rating",
    "Conclusion": "Mocked Conclusion"
}


def test_review_endpoint():
    with patch('app.main.fetch_repo') as mock_fetch_repo:
        mock_fetch_repo.return_value = Repository(
            owner="test",
            repo_name="test",
            file_paths=["folder1/test1.py", "test.py"],
            merged_code=test_repo_code
        )
        with patch('app.main.get_code_review') as mock_review:
            mock_review.return_value = Review(
                downsides_comments="Mocked Downsides",
                rating="Mocked Rating",
                conclusion="Mocked Conclusion"
            )
            response = client.post("/review/",
                                   json={"github_repo_url": "https://github.com/test/test",
                                         "assignment_description": "Write a hello world program",
                                         "candidate_level": "Junior"})
            assert response.status_code == 200
            assert response.json() == test_responce


def test_review_endpoint_missing_fields():
    response = client.post("/review/", json={"github_repo_url": "https://github.com/test/test"})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_review_endpoint_invalid_url():
    # mock_fetch_repo.side_effect = ValueError("Invalid GitHub repository URL format.")
    response = client.post("/review/",
                           json={"github_repo_url": "invalid//url",
                                 "assignment_description": "Write a hello world program",
                                 "candidate_level": "Junior"})
    assert response.status_code == 422
    assert "detail" in response.json()

def test_review_endpoint_invalid_github_url():
    # mock_fetch_repo.side_effect = ValueError("Invalid GitHub repository URL format.")
    response = client.post("/review/",
                           json={"github_repo_url": "https://github.com/bad-url",
                                 "assignment_description": "Write a hello world program",
                                 "candidate_level": "Junior"})
    assert response.status_code == 400
    assert "Invalid GitHub repository URL format. It should be 'https://github.com/owner/repo'" in response.json().get("detail", "")


def test_review_endpoint_github_error():
    with patch('app.github_fetcher.get_repo_info') as mock_fetch_repo:
        url_to_bad_repo = "https://github.com/test/test_repo"
        mock_fetch_repo.side_effect = Exception(f"Failed to retrieve data from {url_to_bad_repo}")
        response = client.post("/review/", json={"github_repo_url": url_to_bad_repo,
                                                 "assignment_description": "Write a hello world program",
                                                 "candidate_level": "Junior"})
        assert response.status_code == 500
        assert f"Internal Server Error: Failed to retrieve data from {url_to_bad_repo}" in response.json().get("detail", "")
