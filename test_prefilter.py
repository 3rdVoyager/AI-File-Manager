import tempfile
import os
from scripts.analysis import pre_analyze_filter

with tempfile.TemporaryDirectory() as tmpdir:
    # Create test files
    files = [
        'archive.zip',
        'installer.exe',
        'Thumbs.db',
        'readme.txt',
    ]
    for f in files:
        open(os.path.join(tmpdir, f), 'w').close()
    
    print('Testing pre_analyze_filter:')
    for f in files:
        result = pre_analyze_filter(os.path.join(tmpdir, f))
        if result:
            print(f'  {f}: {result["category"]} / {result["subcategory"]}')
        else:
            print(f'  {f}: None (needs AI)')