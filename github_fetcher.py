import requests
import os
import base64

import utils

ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')

def make_github_request(url):
    """
    Makes a GET request to the specified GitHub API URL with the necessary headers.

    Parameters:
        url (str): The GitHub API URL.

    Returns:
        dict: The JSON response from the GitHub API.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if ACCESS_TOKEN:
        headers["Authorization"] = f"token {ACCESS_TOKEN}"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to retrieve data from {url}: {response.status_code} {response.text}")

def get_repo_info(repo_url:str):
    """
    Fetches metadata of a repository based on its URL.
    """
    try:
        owner, repo_name = repo_url.rstrip('/').split('/')[-2:]
    except ValueError:
        raise ValueError("Invalid GitHub repository URL format. It should be 'https://github.com/owner/repo'.")

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    return make_github_request(api_url)

def get_repo_tree(owner, repo_name, branch='main'):
    """
    Fetches the file tree of a repository for the given branch.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1"
    return make_github_request(api_url)

# TODO make asynchronous
def fetch_file(owner, repo_name, file_path):
    """
    Fetches the content of a file from the repository.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}"
    file_data = make_github_request(api_url)

    return file_data


def fetch_list_text_files(owner, repo_name, textfile_paths):
    """
    Fetches content for all text files in the given list of file paths.

    Returns:
        dict: A dictionary where the keys a
        re file paths and values are the file contents.
    """
    files = {}
    for file_path in textfile_paths:
        try:
            print(f"Fetching file: {file_path}")
            file_data = fetch_file(owner, repo_name, file_path)

            # Decode the file content (base64 encoded)
            file_text = base64.b64decode(file_data['content']).decode('utf-8')

            files[file_path] = file_text
        except Exception as e:
            print(f"Failed to fetch or process {file_path}: {e}")
    return files


def fetch_repo(repo_url):

    # verify repo exists and is readable by fetching it's metadata
    repo_info = get_repo_info(repo_url)
    owner = repo_info['owner']['login']
    repo_name = repo_info['name']
    default_branch = repo_info['default_branch']

    repo_tree = get_repo_tree(owner, repo_name, default_branch)

    # Extract paths of all files (blobs) and build the directory tree
    file_paths = [item['path'] for item in repo_tree['tree'] if item['type'] == 'blob']

    textfile_paths = [item for item in file_paths if utils.is_text_file(item)]
    # Fetch all cleartext file contents
    files_content = fetch_list_text_files(owner, repo_name, textfile_paths)

    # Merge the fetched file contents into a single string
    merged_code = utils.merge_file_contents(files_content)
    repository = {
        "owner": owner,
        "repo_name": repo_name,
        "file_paths": file_paths,
        "merged_code": merged_code
    }
    return repository

def main():
    repo_url = "https://github.com/Utilka/Test_Repository/"
    repository = fetch_repo(repo_url)

    # Print the directory tree
    directory_tree = utils.build_directory_tree(repository["file_paths"])
    directory_tree_string = utils.print_directory_tree(directory_tree)
    print(directory_tree_string)

    print("\nMerged Content of Text Files:\n")
    print(repository["merged_code"])


if __name__ == '__main__':
    main()
