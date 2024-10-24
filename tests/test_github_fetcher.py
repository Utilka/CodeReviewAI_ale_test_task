import pytest
from unittest.mock import patch, Mock
import base64
from dataclasses import dataclass
from typing import List

from app.github_fetcher import (
    make_github_request,
    get_repo_info,
    get_repo_tree,
    fetch_file,
    fetch_list_text_files,
    fetch_repo,
    Repository,
)
import app.utils as utils


def test_make_github_request_success(monkeypatch):
    url = 'https://api.github.com/repos/owner/repo'

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'key': 'value'}

    # Mock requests.get to return the mock_response
    with patch('requests.get', return_value=mock_response) as mock_get:
        # Ensure ACCESS_TOKEN is not set
        monkeypatch.setattr('app.github_fetcher.ACCESS_TOKEN', None)
        response = make_github_request(url)
        mock_get.assert_called_once_with(url, headers={'Accept': 'application/vnd.github.v3+json'})
        assert response == {'key': 'value'}


def test_make_github_request_with_token(monkeypatch):
    url = 'https://api.github.com/repos/owner/repo'
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'key': 'value'}

    with patch('requests.get', return_value=mock_response) as mock_get:
        # Set fake ACCESS_TOKEN
        monkeypatch.setattr('app.github_fetcher.ACCESS_TOKEN', 'fake_token')
        response = make_github_request(url)
        mock_get.assert_called_once_with(
            url,
            headers={
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': 'token fake_token',
            },
        )
        assert response == {'key': 'value'}


def test_make_github_request_failure():
    url = 'https://api.github.com/repos/owner/repo'
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = 'Not Found'

    with patch('requests.get', return_value=mock_response):
        with pytest.raises(Exception) as excinfo:
            make_github_request(url)
        assert 'Failed to retrieve data from' in str(excinfo.value)


def test_get_repo_info_success():
    repo_url = 'https://github.com/owner/repo'
    # Mock make_github_request to return some data
    with patch('app.github_fetcher.make_github_request') as mock_make_request:
        mock_make_request.return_value = {'key': 'value'}
        response = get_repo_info(repo_url)
        api_url = 'https://api.github.com/repos/owner/repo'
        mock_make_request.assert_called_once_with(api_url)
        assert response == {'key': 'value'}


def test_get_repo_info_invalid_url():
    repo_url = 'https://github.com/owner'  # Missing repo name
    with pytest.raises(ValueError) as excinfo:
        get_repo_info(repo_url)
    assert 'Invalid GitHub repository URL format' in str(excinfo.value)


def test_get_repo_tree():
    owner = 'owner'
    repo_name = 'repo'
    branch = 'main'

    with patch('app.github_fetcher.make_github_request') as mock_make_request:
        mock_make_request.return_value = {'tree': []}
        response = get_repo_tree(owner, repo_name, branch)
        api_url = f'https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1'
        mock_make_request.assert_called_once_with(api_url)
        assert response == {'tree': []}


def test_fetch_file():
    owner = 'owner'
    repo_name = 'repo'
    file_path = 'path/to/file'

    with patch('app.github_fetcher.make_github_request') as mock_make_request:
        mock_make_request.return_value = {'content': 'ZmlsZSBjb250ZW50'}  # base64 encoded 'file content'
        response = fetch_file(owner, repo_name, file_path)
        api_url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}'
        mock_make_request.assert_called_once_with(api_url)
        assert response == {'content': 'ZmlsZSBjb250ZW50'}


def test_fetch_list_text_files():
    owner = 'owner'
    repo_name = 'repo'
    textfile_paths = ['file1.txt', 'file2.txt']

    # Mock fetch_file to return mock file data
    with patch('app.github_fetcher.fetch_file') as mock_fetch_file:
        # Set side effects for each call
        mock_fetch_file.side_effect = [
            {'content': base64.b64encode(b'content of file1').decode('utf-8')},
            {'content': base64.b64encode(b'content of file2').decode('utf-8')},
        ]

        files = fetch_list_text_files(owner, repo_name, textfile_paths)
        assert files == {
            'file1.txt': 'content of file1',
            'file2.txt': 'content of file2',
        }


def test_fetch_list_text_files_exception():
    owner = 'owner'
    repo_name = 'repo'
    textfile_paths = ['file1.txt', 'file2.txt']

    # Mock fetch_file to raise an exception on the second file
    with patch('app.github_fetcher.fetch_file') as mock_fetch_file:
        mock_fetch_file.side_effect = [
            {'content': base64.b64encode(b'content of file1').decode('utf-8')},
            Exception('Failed to fetch file'),
        ]

        # Capture the output to check the print statements
        with patch('builtins.print') as mock_print:
            files = fetch_list_text_files(owner, repo_name, textfile_paths)
            # Only file1 should be in files
            assert files == {'file1.txt': 'content of file1'}
            # Check that the exception message was printed
            mock_print.assert_any_call('Fetching file: file1.txt')
            mock_print.assert_any_call('Fetching file: file2.txt')
            mock_print.assert_any_call('Failed to fetch or process file2.txt: Failed to fetch file')


def test_fetch_repo():
    repo_url = 'https://github.com/owner/repo'

    repo_info = {
        'owner': {'login': 'owner'},
        'name': 'repo',
        'default_branch': 'main',
    }

    repo_tree = {
        'tree': [
            {'path': 'file1.txt', 'type': 'blob'},
            {'path': 'file2.bin', 'type': 'blob'},
            {'path': 'dir/file3.txt', 'type': 'blob'},
        ]
    }

    textfile_paths = ['file1.txt', 'dir/file3.txt']
    files_content = {
        'file1.txt': 'content of file1',
        'dir/file3.txt': 'content of file3',
    }

    merged_code = 'merged content'

    with patch('app.github_fetcher.get_repo_info', return_value=repo_info) as mock_get_repo_info, \
         patch('app.github_fetcher.get_repo_tree', return_value=repo_tree) as mock_get_repo_tree, \
         patch('app.github_fetcher.utils.is_text_file', side_effect=lambda x: x.endswith('.txt')) as mock_is_text_file, \
         patch('app.github_fetcher.fetch_list_text_files', return_value=files_content) as mock_fetch_list_text_files, \
         patch('app.github_fetcher.utils.merge_file_contents', return_value=merged_code) as mock_merge_file_contents:

        repository = fetch_repo(repo_url)

        mock_get_repo_info.assert_called_once_with(repo_url)
        mock_get_repo_tree.assert_called_once_with('owner', 'repo', 'main')
        # Check that utils.is_text_file was called correctly
        called_paths = [call[0][0] for call in mock_is_text_file.call_args_list]
        assert set(called_paths) == {'file1.txt', 'file2.bin', 'dir/file3.txt'}
        mock_fetch_list_text_files.assert_called_once_with('owner', 'repo', textfile_paths)
        mock_merge_file_contents.assert_called_once_with(files_content)

        # Check the repository object
        assert repository.owner == 'owner'
        assert repository.repo_name == 'repo'
        assert repository.file_paths == ['file1.txt', 'file2.bin', 'dir/file3.txt']
        assert repository.merged_code == 'merged content'
