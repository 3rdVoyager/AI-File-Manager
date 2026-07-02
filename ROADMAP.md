# Version 0.1

The user runs:

```bash
python main.py
```

It asks:

```
Enter the path to a file:
>
```

The user enters:

```
C:\Users\Joshua\Documents\Homework\essay.txt
```

Your program:

- Checks the file exists
- Reads the text
- Gets metadata:
  - filename
  - size
  - creation/modification dates
- Sends it to an LLM
- Prints the response

Output might look like:

```
========================
File Analysis
========================

Filename:
  essay.txt

Type:
  Text

Size:
  12.4 KB

Summary:
  This is an English essay discussing renewable energy.

Category:
  School

Recommendation:
  Keep

Reason:
  This appears to be a completed school assignment and may be useful for future reference.

Suggested Filename:
  Renewable Energy Essay.txt
```

---

# Version 0.2

Instead of analyzing one file, analyze every `.txt` file in a folder.

```
Enter folder:
>
```

Then:

```
Found 18 text files...

Analyzing...
```

Afterwards:

## Results

### KEEP

- `notes.txt`
- `essay.txt`
- `journal.txt`

### DELETE CANDIDATES

- `test123.txt`
- `asdf.txt`
- `copy copy.txt`

### RENAME

- `notes.txt` ↓
  `Python Requests Notes.txt`

---

# Version 0.3

Introduce caching with SQLite.

Suppose you've already analyzed:

```
essay.txt
```

If nothing has changed:

```
✓ Cached result found
```

Instead of spending API credits again.

That will become incredibly valuable once you're scanning hundreds or thousands of files.

---

# Version 0.4

Now start supporting more formats.

For example:

- `.txt`
- `.md`
- `.py`
- `.js`
- `.html`
- `.css`
- `.json`
- `.pdf`

Most of these are just text or can be converted to text before sending to the model.