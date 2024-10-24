from app.utils import build_directory_tree, format_directory_tree, is_text_file, merge_file_contents


def test_build_directory_tree():
    paths = ["folder1/file1.py", "folder1/file2.py", "folder2/file3.py"]
    tree = build_directory_tree(paths)
    assert "folder1" in tree
    assert "folder2" in tree
    assert "file1.py" in tree["folder1"]
    assert "file2.py" not in tree["folder2"]


def test_print_directory_tree():
    tree = {"folder1": {"file1.py": {}, "file2.py": {}}, "folder2": {"file3.py": {}}}
    tree_str = format_directory_tree(tree)
    assert "├── folder1" in tree_str
    assert "├── folder2" in tree_str


def test_is_text_file():
    assert is_text_file("example.py") is True
    assert is_text_file("example.png") is False


def test_merge_file_contents():
    files = {"file1.py": "print(\"Hello\")", "file2.py": "print(\"World\")"}
    merged_content = merge_file_contents(files)
    assert "--- file1.py ---" in merged_content
    assert "print(\"World\")" in merged_content
