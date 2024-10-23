from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

from github_fetcher import fetch_repo
from openAI_reviewer import get_code_review

app = FastAPI()

# Endpoint Specification:
# POST /review - Accept the following data in the request body:
# - assignment_description: string (description of the ceding assignment)
# - github_repo_url: string (URL of the GitHub repository to review)
# - candidate_level: string (Junior, Middle, or Senior)
#
# - The endpoint should:
# 1. Use the GitHub API to fetch the repository contents.
# 2. Use OpenAfs GPT API to analyze the code and generate a review.
# 3. Return the review result (text) in the following format: Found files, Downsides/Comments, Rating, Conclusion

class CandidateLevel(str,Enum):
    junior = "Junior"
    middle = "Middle"
    Senior = "Senior"

    #make the field case-insensitive
    @classmethod
    def _missing_(cls, value:str):
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        return None

class DefaultModel(BaseModel):
    assignment_description: str = Field(..., description="Description of the assignment.")
    github_repo_url: HttpUrl = Field(..., description="URL pointing to the target repository.")
    candidate_level: CandidateLevel = Field(..., description="Competency level of the candidate.")

    @field_validator('github_repo_url')
    def validate_github_repo_url(cls, value: HttpUrl) -> HttpUrl:
        if not value.host or 'github.com' != value.host:
            raise HTTPException(
                status_code=400,
                detail="The provided URL must be a GitHub repository URL."
            )
        return value

@app.post("/review")
async def code_review(params: DefaultModel):
    repo = fetch_repo(str(params.github_repo_url))
    review = get_code_review(repo.merged_code, params.assignment_description, params.candidate_level)
    return {
        "Found files": repo.file_paths,
        "Downsides/Comments": review.downsides_comments,
        "Rating": review.rating,
        "Conclusion": review.conclusion,
    }