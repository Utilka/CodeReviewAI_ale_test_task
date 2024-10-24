import base64
import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import List

import aiohttp
import asyncio

from . import utils

logger = logging.getLogger(__name__)
ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')

# Initialize a deque to keep track of request timestamps
REQUEST_TIMES = deque()
# Determine the per-minute limit based on whether an access token is used
PER_HOUR_LIMIT = 5000 if ACCESS_TOKEN else 60
PER_MINUTE_LIMIT = PER_HOUR_LIMIT // 60  # Integer division to get whole requests per minute

# Create an asyncio.Lock for thread safety in rate limiting
rate_limit_lock = asyncio.Lock()

async def make_github_request(url):
    """
    Asynchronously makes a GET request to the specified GitHub API URL with the necessary headers,
    enforcing rate limits based on GitHub's per-hour limits.

    Parameters:
        url (str): The GitHub API URL.

    Returns:
        dict: The JSON response from the GitHub API.

    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    logger.info(f"Making GitHub API request to URL: {url}")
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if ACCESS_TOKEN:
        headers["Authorization"] = f"token {ACCESS_TOKEN}"

    # Enforce rate limiting with thread safety
    async with rate_limit_lock:
        current_time = time.time()
        # Remove timestamps older than 60 seconds
        while REQUEST_TIMES and REQUEST_TIMES[0] <= current_time - 60:
            REQUEST_TIMES.popleft()

        if len(REQUEST_TIMES) >= PER_MINUTE_LIMIT:
            # Calculate how long to sleep until we can make the next request
            sleep_time = 60 - (current_time - REQUEST_TIMES[0])
            logger.info(f"Rate limit exceeded. Sleeping for {sleep_time:.2f} seconds")

            await asyncio.sleep(sleep_time)

            # Update current time after sleeping
            current_time = time.time()
            # Clean up old timestamps after sleeping
            while REQUEST_TIMES and REQUEST_TIMES[0] <= current_time - 60:
                REQUEST_TIMES.popleft()

        # Append the current timestamp to the deque
        REQUEST_TIMES.append(current_time)

    # Make the asynchronous HTTP request
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                logger.debug(f"GitHub API request successful. Status code: {response.status}")
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Failed to retrieve data from {url}: {response.status} {text}")

async def get_repo_info(repo_url: str):
    """
    Fetches metadata of a repository based on its URL.

    Parameters:
        repo_url (str): The GitHub repository URL.

    Returns:
        dict: Repository information from the GitHub API.

    Raises:
        ValueError: If the repository URL format is invalid.
        Exception: If fetching repository info fails.
    """
    logger.info(f"Getting repository info for URL: {repo_url}")
    try:
        # Extract owner and repository name from the URL
        location = repo_url.replace("https://github.com/", "")
        owner, repo_name = location.rstrip('/').split('/')[-2:]
    except ValueError:
        logger.error("Invalid GitHub repository URL format.")
        raise ValueError("Invalid GitHub repository URL format. It should be 'https://github.com/owner/repo'.")

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    logger.debug(f"GitHub API URL for repository info: {api_url}")
    return await make_github_request(api_url)

async def get_repo_tree(owner, repo_name, branch='main'):
    """
    Fetches the file tree of a repository for the given branch.

    Parameters:
        owner (str): The GitHub username or organization.
        repo_name (str): The name of the repository.
        branch (str): The branch to fetch the tree from.

    Returns:
        dict: The repository tree structure from the GitHub API.

    Raises:
        Exception: If fetching the repository tree fails.
    """
    logger.info(f"Getting repository tree for {owner}/{repo_name} at branch {branch}")
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1"
    logger.debug(f"GitHub API URL for repository tree: {api_url}")
    return await make_github_request(api_url)

async def fetch_file(owner, repo_name, file_path):
    """
    Fetches the content of a file from the repository.

    Parameters:
        owner (str): The GitHub username or organization.
        repo_name (str): The name of the repository.
        file_path (str): The path to the file in the repository.

    Returns:
        dict: The file content and metadata from the GitHub API.

    Raises:
        Exception: If fetching the file fails.
    """
    logger.info(f"Fetching file {file_path} from {owner}/{repo_name}")
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}"
    return await make_github_request(api_url)

async def fetch_list_text_files(owner, repo_name, textfile_paths):
    """
    Fetches content for all text files in the given list of file paths.

    Parameters:
        owner (str): The GitHub username or organization.
        repo_name (str): The name of the repository.
        textfile_paths (list): A list of text file paths to fetch.

    Returns:
        dict: A dictionary where keys are file paths and values are the file contents.
    """
    files = {}

    async def fetch_and_store(file_path):
        try:
            logger.info(f"Fetching file: {file_path}")
            file_data = await fetch_file(owner, repo_name, file_path)
            # Decode the file content (base64 encoded)
            file_text = base64.b64decode(file_data['content']).decode('utf-8')
            files[file_path] = file_text
        except Exception as e:
            logger.error(f"Failed to fetch or process {file_path}: {e}")

    tasks = [fetch_and_store(file_path) for file_path in textfile_paths]
    await asyncio.gather(*tasks)
    return files

@dataclass
class Repository:
    owner: str
    repo_name: str
    file_paths: List[str]
    merged_code: str

async def fetch_repo(repo_url):
    """
    Fetches the repository's file contents and metadata.

    Parameters:
        repo_url (str): The GitHub repository URL.

    Returns:
        Repository: An object containing repository details and merged code.

    Raises:
        Exception: If any step in fetching the repository fails.
    """
    logger.info(f"Fetching repository from URL: {repo_url}")

    # Verify repo exists and is readable by fetching its metadata
    try:
        repo_info = await get_repo_info(repo_url)
    except Exception as e:
        logger.error(f"Error fetching repository info: {e}")
        raise

    owner = repo_info['owner']['login']
    repo_name = repo_info['name']
    default_branch = repo_info['default_branch']

    logger.info(f"Repository info retrieved: owner={owner}, repo_name={repo_name}, default_branch={default_branch}")

    # Fetch the repository tree
    try:
        repo_tree = await get_repo_tree(owner, repo_name, default_branch)
    except Exception as e:
        logger.error(f"Error fetching repository tree: {e}")
        raise

    # Extract paths of all files (blobs)
    file_paths = [item['path'] for item in repo_tree['tree'] if item['type'] == 'blob']

    # Filter out text files
    textfile_paths = [item for item in file_paths if utils.is_text_file(item)]

    # Fetch all text file contents
    try:
        files_content = await fetch_list_text_files(owner, repo_name, textfile_paths)
    except Exception as e:
        logger.error(f"Error fetching file contents: {e}")
        raise

    # Merge the fetched file contents into a single string
    merged_code = utils.merge_file_contents(files_content)

    repository = Repository(
        owner=owner,
        repo_name=repo_name,
        file_paths=file_paths,
        merged_code=merged_code
    )

    logger.info(f"Repository fetched successfully: {owner}/{repo_name}")
    return repository
