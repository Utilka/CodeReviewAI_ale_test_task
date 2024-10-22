import mimetypes

def build_directory_tree(file_paths):
    """
    Builds a nested dictionary structure representing the directory tree.
    """
    tree = {}
    for path in file_paths:
        parts = path.split('/')
        current_level = tree
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]
    return tree


def print_directory_tree(tree, indent=""):
    """
    Recursively generates a string representation of the directory tree.
    """
    tree_string = ""
    for key, value in sorted(tree.items()):
        tree_string += f"{indent}├── {key}\n"
        if isinstance(value, dict):
            # Add files/subdirectories with increased indentation
            tree_string += print_directory_tree(value, indent + "    ")
    return tree_string


def is_text_file(file_path):
    """
    Determines if a file is likely a text file based on its mime type.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type and mime_type.startswith('text')


def merge_file_contents(files):
    """
    Merges the content of all files into a single string, separated by file names.

    Parameters:
        files (dict): A dictionary where keys are file paths and values are file contents.

    Returns:
        str: A single string containing all merged file contents.
    """
    merged_content = ""
    for file_path, content in files.items():
        merged_content += f"\n--- {file_path} ---\n"
        merged_content += content + "\n"
    return merged_content