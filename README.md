# AI File Manager

An intelligent file organization system that uses AI to analyze, categorize, and recommend actions for your files.

---

## Features

- **File Analysis**: Examine individual files and extract metadata (name, size, creation/modification dates)
- **AI-Powered Insights**: Send file contents to an LLM for smart categorization and recommendations
- **Action Recommendations**: Get suggestions on whether to keep, delete, or rename files
- **Batch Processing**: Analyze all files of a specific type in a directory
- **Caching**: SQLite-based caching to avoid re-analyzing unchanged files
- **Multi-Format Support**: Handle various file formats including `.txt`, `.md`, `.py`, `.js`, `.html`, `.css`, `.json`, `.pdf`

---

## Installation

```bash
# Clone the repository
git clone https://github.com/3rdVoyager/ai-file-manager.git
cd ai-file-manager

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Analyze a Single File

```bash
python main.py
```

The program will prompt you to enter a file path. It will then:
1. Verify the file exists
2. Read and analyze its contents
3. Extract metadata
4. Send the data to an LLM
5. Display analysis results with recommendations

### Analyze Multiple Files

When prompted, enter a directory path to analyze all supported files within that folder.

---

## Project Structure

```
AI-File-Manager/
├── AIFileOrganizer/
│   ├── main.py          # Entry point and CLI interface
│   ├── gui.py           # Graphical user interface (future)
│   ├── scanner.py       # File scanning and discovery
│   ├── vision.py        # Computer vision for non-text files (future)
│   ├── reasoning.py     # AI reasoning and analysis logic
│   ├── database.py      # SQLite caching and persistence
│   ├── renamer.py       # File renaming utilities
│   ├── utils.py         # Helper functions and utilities
│   └── assets/
│       └── icons/       # Application icons
├── README.md
└── ROADMAP.md
```

---

## Configuration

Create a `.env` file in the project root to configure your API keys:

```env
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4  # or your preferred model
MAX_FILE_SIZE_MB=10  # Maximum file size to analyze
```

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed version plans and upcoming features.

---

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
