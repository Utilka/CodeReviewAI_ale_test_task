import requests
import os

def get_repo_info(repo_url, access_token=None):
    # Extract the owner and repo name from the URL
    try:
        owner, repo_name = repo_url.rstrip('/').split('/')[-2:]
    except ValueError:
        raise ValueError("Invalid GitHub repository URL format. It should be 'https://github.com/owner/repo'.")

    # GitHub API URL for repository details
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    # Set up headers, including access token if provided
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if access_token:
        headers["Authorization"] = f"token {access_token}"

    # Make a GET request to the GitHub API
    response = requests.get(api_url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        return response.json()  # Return the JSON response containing repository information
    else:
        raise Exception(f"Failed to retrieve repository information: {response.status_code} {response.text}")

if __name__ == '__main__':

    # Example usage:
    repo_url = "https://github.com/Utilka/Test_Repository/"
    # access_token  = os.getenv('GITHUB_ACCESS_TOKEN')

    try:
        repo_info = get_repo_info(repo_url)
        print(f"Repository Name: {repo_info['name']}")
        print(f"Description: {repo_info['description']}")
        print(f"Stars: {repo_info['stargazers_count']}")
        print(f"Forks: {repo_info['forks_count']}")
        print(f"Open Issues: {repo_info['open_issues_count']}")
    except Exception as e:
        print(e)
