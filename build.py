import os
import zipfile
from fnmatch import fnmatch

PKG_NAME = 'SEILAPLAN'
# Includes all the top level paths that should be included when building the zip file
TOP_LEVEL_INCLUDES = [
    'config',
    'core',
    'gui',
    'help',
    'i18n',
    'img',
    'lib',
    'tools',
    'utils',
    '__init__.py',
    'changelog.md',
    'LICENSE',
    'metadata.txt',
    'README.md',
    'seilaplanPlugin.py',
    'seilaplanRun.py'
]
# Search for these patterns to exclude folders and files
PATTERN_EXCLUDES = [
    '__pycache__',
    '.pro',
    '.ts',
    'set_german_translation',
    'commonPaths.txt',
    '_pole_symbols.svg',
]


def create_zip(zip_path, folder_path, top_level_includes, ignore_patterns):
    print('Creating ZIP archive ' + zip_path)
    includedPaths = [os.path.join(folder_path, folder) for folder in top_level_includes]
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, folders, files in os.walk(folder_path):
            for file in files:
                path = str(os.path.join(root, file))
                if not any([path.startswith(str(includedPath))
                               for includedPath in includedPaths]):
                    # Path does not start with a path from the include list, skip it
                    continue
                archive_path = str(os.path.relpath(
                        os.path.join(root, file),
                        os.path.join(folder_path, os.pardir)))
                if not any(fnmatch(path, '*' + ignore + '*') for ignore in ignore_patterns):
                    print('Adding ' + archive_path)
                    zipf.write(path, archive_path)
                else:
                    print('Ignoring ' + archive_path)
    print('Created ZIP archive ' + zip_path)


if __name__ == '__main__':
    # Path to plugin folder we want to deploy
    plugin_dir = os.path.dirname(__file__)
    deploy_path = os.path.dirname(plugin_dir)
    zip_file = os.path.join(deploy_path, PKG_NAME + '.zip')

    try:
        # Clean up
        os.remove(zip_file)
    except FileNotFoundError:
        pass
    
    # Zip content of plugin
    create_zip(zip_file, plugin_dir, TOP_LEVEL_INCLUDES, PATTERN_EXCLUDES)
