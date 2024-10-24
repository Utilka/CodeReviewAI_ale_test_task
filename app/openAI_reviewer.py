import logging
import asyncio
import time
from dataclasses import dataclass
from collections import deque

import openai

# Ensure your OpenAI API key is set in the environment variable OPENAI_API_KEY

logger = logging.getLogger(__name__)

@dataclass
class Review:
    downsides_comments: str
    rating: str
    conclusion: str

# Define rate limit parameters
RATE_LIMIT = 500  # Number of requests per minute; adjust based on your OpenAI account's rate limits
REQUEST_TIMES = deque()

async def rate_limited_openai_chat_completion(model, messages):
    """
    Helper function to handle rate limiting and make asynchronous OpenAI API calls.

    Parameters:
        model (str): The OpenAI model to use.
        messages (list): The messages to send to the OpenAI API.

    Returns:
        dict: The completion response from the OpenAI API.
    """
    current_time = time.time()
    # Remove timestamps older than 60 seconds
    while REQUEST_TIMES and REQUEST_TIMES[0] <= current_time - 60:
        REQUEST_TIMES.popleft()

    if len(REQUEST_TIMES) >= RATE_LIMIT:
        sleep_time = 60 - (current_time - REQUEST_TIMES[0])
        logger.info(f"OpenAI rate limit exceeded. Sleeping for {sleep_time:.2f} seconds")

        await asyncio.sleep(sleep_time)

        # Update current time after sleeping
        current_time = time.time()
        # Clean up old timestamps after sleeping
        while REQUEST_TIMES and REQUEST_TIMES[0] <= current_time - 60:
            REQUEST_TIMES.popleft()

    # Append the current timestamp to the deque
    REQUEST_TIMES.append(current_time)

    # Make the asynchronous OpenAI API call
    try:
        completion = openai.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}")
        raise

async def get_code_review(code, assignment, reviewed_level):
    """
    Generates a code review using OpenAI's GPT API.

    Parameters:
        code (str): The code to be reviewed.
        assignment (str): The assignment description.
        reviewed_level (str): The competency level of the candidate.

    Returns:
        Review: An object containing downsides/comments, rating, and conclusion.
    """
    logger.info("Starting code review.")
    logger.debug(f"Assignment: {assignment}")
    logger.debug(f"Reviewed level: {reviewed_level}")

    # First API call: Get downsides and comments
    logger.info("Making OpenAI API call for downsides and comments.")
    try:
        downsides_comments_completion = await rate_limited_openai_chat_completion(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in computer programming, performing a code review of the provided code repository. "
                        f"The repository was written by a {reviewed_level} programmer and should be held to corresponding standards. "
                        f"Their assignment was: {assignment} "
                        "Your current task is to find downsides and write comments on the provided repository."
                    )
                },
                {"role": "user", "content": code}
            ]
        )
        logger.debug("OpenAI API call for downsides and comments completed successfully.")
    except Exception as e:
        logger.error(f"Error during OpenAI API call for downsides and comments: {e}")
        raise

    # Extract the content from the completion response
    downsides_comments = downsides_comments_completion.choices[0].message.content

    # Second API call: Get rating
    logger.info("Making OpenAI API call for rating.")
    try:
        rating_completion = await rate_limited_openai_chat_completion(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in computer programming, performing a code review of the provided code repository. "
                        f"The repository was written by a {reviewed_level} programmer and should be held to corresponding standards. "
                        f"Their assignment was: {assignment} "
                        "Your current task is to rate the provided repository on a scale from 0 to 100. "
                        "You should be brief in your reasoning."
                    )
                },
                {"role": "user", "content": code},
                {"role": "assistant", "content": downsides_comments}
            ]
        )
        logger.debug("OpenAI API call for rating completed successfully.")
    except Exception as e:
        logger.error(f"Error during OpenAI API call for rating: {e}")
        raise

    # Extract the content from the completion response
    rating = rating_completion.choices[0].message.content

    # Third API call: Get conclusion
    logger.info("Making OpenAI API call for conclusion.")
    try:
        conclusion_completion = await rate_limited_openai_chat_completion(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in computer programming, performing a code review of the provided code repository. "
                        f"The repository was written by a {reviewed_level} programmer and should be held to corresponding standards. "
                        f"Their assignment was: {assignment} "
                        "Your current task is to draw conclusions on the provided code repository and suggest ways to improve it. "
                        "Do not propose to the user to continue the conversation; this message is final."
                    )
                },
                {"role": "user", "content": code},
                {"role": "assistant", "content": downsides_comments},
                {"role": "assistant", "content": rating},
            ]
        )
        logger.debug("OpenAI API call for conclusion completed successfully.")
    except Exception as e:
        logger.error(f"Error during OpenAI API call for conclusion: {e}")
        raise

    # Extract the content from the completion response
    conclusion = conclusion_completion.choices[0].message.content

    # Create and return the Review object
    review = Review(
        downsides_comments=downsides_comments,
        rating=rating,
        conclusion=conclusion
    )

    logger.info("Code review completed successfully.")
    return review
