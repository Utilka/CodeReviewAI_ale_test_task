import sys
from enum import Enum

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi_cache.decorator import cache
from pydantic import BaseModel, Field, HttpUrl, field_validator

from .github_fetcher import fetch_repo
from .openAI_reviewer import get_code_review

from fastapi_cache import FastAPICache,decorator
import hashlib


app = FastAPI()

def setup_cache(app):
    def request_key_builder(
            func,
            namespace: str = "",
            request: Request = None,
            response: Response = None,
            *args,
            **kwargs,
    ):

        print(f"aaaaaaaaaaaaaaaaaaaaaaaaaaa")
        # body_hash = hashlib.md5(await request.body()).hexdigest() if request.method in ["post", "put"] else ""
        #
        # print(f"jija cache request body: {await request.body()}")
        # print(f"jija cache request hash: {body_hash}")
        return ":".join([
            namespace,
            request.method.lower(),
            request.url.path,
            repr(sorted(request.query_params.items())),
            # body_hash
        ])

    @app.on_event("startup")
    async def startup():

        print(f"startup aaaaaaaaaaaaaaaaaaaaaaaaaaa")
        if 'win' in sys.platform:
            from fastapi_cache.backends.inmemory import InMemoryBackend
            FastAPICache.init(InMemoryBackend())
        else:
            from redis import asyncio as aioredis
            from fastapi_cache.backends.redis import RedisBackend
            # logger.info("Connecting to Redis")
            redis = aioredis.from_url("redis://redis:6379/0")
            if not redis:
                raise Exception("Cannot connect to Redis")
            FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
            print("jija successfully initialised")

    return request_key_builder

keybuilder = setup_cache(app)


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
@cache(expire=3600,key_builder = keybuilder)
async def code_review(params: DefaultModel):
    print("aboba request recieved")
    repo = fetch_repo(str(params.github_repo_url))
    review = get_code_review(repo.merged_code, params.assignment_description, params.candidate_level)
    return {
        "Found files": repo.file_paths,
        "Downsides/Comments": review.downsides_comments,
        "Rating": review.rating,
        "Conclusion": review.conclusion,
    }

