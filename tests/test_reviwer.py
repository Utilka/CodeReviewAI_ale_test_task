# tests/test_reviwer.py
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from app.openAI_reviewer import get_code_review, Review

mock_review = Review(
    downsides_comments="The code is functional but lacks comments and documentation.",
    rating="Rating: 85/100. The code works but can be improved with documentation.",
    conclusion="Consider adding comments and a more detailed README to enhance code clarity."
)
code = """--- Directory/test.py ---
print("Hello World from test directory!")


--- README.md ---
# Test_Repository

--- main.py ---
print("Hello World!")
"""

@pytest.mark.asyncio
async def test_get_code_review():
    # Sample input
    assignment = "write a hello world program"
    reviewed_level = "Junior"

    # Mock responses for each API call
    downsides_mock_response = MagicMock()
    downsides_mock_response.choices = [MagicMock()]
    downsides_mock_response.choices[0].message.content = mock_review.downsides_comments

    rating_mock_response = MagicMock()
    rating_mock_response.choices = [MagicMock()]
    rating_mock_response.choices[0].message.content = mock_review.rating

    conclusion_mock_response = MagicMock()
    conclusion_mock_response.choices = [MagicMock()]
    conclusion_mock_response.choices[0].message.content = mock_review.conclusion

    # Patch the OpenAI API calls
    with patch('app.openAI_reviewer.openai.chat.completions.create') as mock_create:
        # Set the side effects to return our mock responses in order
        mock_create.side_effect = [
            downsides_mock_response,
            rating_mock_response,
            conclusion_mock_response
        ]

        # Call the function under test
        review = await get_code_review(code, assignment, reviewed_level)

        # Assertions to check if the outputs are as expected
        assert isinstance(review, Review)
        assert review.downsides_comments == mock_review.downsides_comments
        assert review.rating == mock_review.rating
        assert review.conclusion == mock_review.conclusion
