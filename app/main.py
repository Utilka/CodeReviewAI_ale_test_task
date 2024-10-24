from enum import Enum
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

from .github_fetcher import fetch_repo
from .openAI_reviewer import get_code_review

# Configure logging settings
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize the FastAPI application
app = FastAPI()

# Endpoint Specification:
# POST /review - Accept the following data in the request body:
# - assignment_description: string (description of the coding assignment)
# - github_repo_url: string (URL of the GitHub repository to review)
# - candidate_level: string (Junior, Middle, or Senior)
#
# - The endpoint should:
# 1. Use the GitHub API to fetch the repository contents.
# 2. Use OpenAI's GPT API to analyze the code and generate a review.
# 3. Return the review result (text) in the following format: Found files, Downsides/Comments, Rating, Conclusion

class CandidateLevel(str, Enum):
    junior = "Junior"
    middle = "Middle"
    senior = "Senior"

    @classmethod
    def _missing_(cls, value: str):
        """
        Overrides the default _missing_ method to make the enum case-insensitive.
        """
        value_lower = value.lower()
        for member in cls:
            if member.value.lower() == value_lower:
                return member
        return None  # Returns None if the value doesn't match any enum member

class DefaultModel(BaseModel):
    assignment_description: str = Field(..., description="Description of the assignment.")
    github_repo_url: HttpUrl = Field(..., description="URL pointing to the target repository.")
    candidate_level: CandidateLevel = Field(..., description="Competency level of the candidate.")

    @field_validator('github_repo_url')
    def validate_github_repo_url(cls, value: HttpUrl) -> HttpUrl:
        """
        Validates that the provided URL is a GitHub repository URL.
        """
        if not value.host or 'github.com' not in value.host:
            raise HTTPException(
                status_code=400,
                detail="The provided URL must be a GitHub repository URL."
            )
        return value

@app.post("/review")
async def code_review(params: DefaultModel):

    logger.info("Received code review request.")
    logger.debug(f"Request parameters: {params}")

    try:
        # Fetch the repository contents using GitHub API
        repo = await fetch_repo(str(params.github_repo_url))
    except ValueError as ve:
        logger.error(f"ValueError in fetch_repo: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Exception in fetch_repo: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    try:
        # Generate code review using OpenAI's GPT API
        review = await get_code_review(
            repo.merged_code,
            params.assignment_description,
            params.candidate_level.value  # Use the value of the enum member
        )
    except Exception as e:
        logger.error(f"Exception in get_code_review: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    logger.info("Code review completed successfully, returning response.")

    # Return the review results
    return {
        "Found files": repo.file_paths,
        "Downsides/Comments": review.downsides_comments,
        "Rating": review.rating,
        "Conclusion": review.conclusion,
    }
