# Note Assistant

An AI-powered note processing system that automatically watches your Obsidian vault's inbox folder, processes raw notes using Claude API to clean them up, add hashtags, format as bullets, and suggest PARA categorization - all running in the cloud via GitHub Actions.

## Features

- **Automated Processing**: Runs every 10 minutes via GitHub Actions
- **AI Enhancement**: Uses Claude API to clean up and organize notes
- **PARA Method Integration**: Suggests categorization for Projects, Areas, Resources, and Archive
- **Multi-modal Support**: Processes text files, images, and other media
- **Cloud-based**: No need to keep your computer running
- **Safe Processing**: Files marked with underscore immediately, reversible operations

## How It Works

1. **Capture**: Drop raw thoughts, meeting notes, web clips into your Obsidian vault's `0-QuickNotes` folder
2. **Process**: GitHub Actions automatically detects new/modified files every 10 minutes
3. **Enhance**: Claude AI cleans up formatting, adds hashtags, creates summaries, and suggests PARA categorization
4. **Review**: Enhanced notes appear in your inbox with metadata for manual sorting

## Architecture

```
Obsidian Vault (Google Drive)
├── 0-QuickNotes/          # Raw thought dumps (inbox)
├── 1-Projects/            # Active projects with deadlines
├── 2-Areas/               # Ongoing responsibilities  
├── 3-Resources/           # Reference materials
└── 4-Archive/             # Inactive items
```

The system adds structured YAML frontmatter to processed notes:

```yaml
---
processed_datetime: "2025-01-07T14:30:00Z"
note_hash: "sha256:..."
summary: "Brief one-line summary of the note's main topic"
tags: ["#meeting", "#project-alpha", "#action-items"]
para_suggestion: "projects"
confidence_score: 0.85
processing_version: "1.0"
original_length: 1523
---
```

## Setup

### Prerequisites

- Google Drive account with an Obsidian vault
- Anthropic API key
- GitHub account

### Installation

1. **Fork this repository** to your GitHub account

2. **Create a Google Cloud Project** and enable the Google Drive API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Drive API
   - Create a service account and download the JSON credentials
   - Share your Obsidian vault folder with the service account email

3. **Get your Anthropic API key**:
   - Sign up at [Anthropic](https://console.anthropic.com/)
   - Create an API key

4. **Configure GitHub Secrets**:
   Go to your repository Settings → Secrets and variables → Actions, and add:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `GOOGLE_DRIVE_CREDENTIALS`: Base64 encoded service account JSON (run: `base64 -i credentials.json`)
   - `GOOGLE_DRIVE_FOLDER_ID`: The ID of your Obsidian vault folder in Google Drive

5. **Enable GitHub Actions** in your repository settings

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/note-assistant.git
cd note-assistant

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# ANTHROPIC_API_KEY=your_key_here
# GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json
# GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# Run tests
python run_tests.py

# Run locally (for testing)
python run.py
```

## Configuration

### Application Settings

Edit `config/settings.yaml` to customize processing:

```yaml
processing:
  max_note_size_kb: 100     # Maximum note size to process
  max_notes_per_run: 10     # Limit notes per GitHub Actions run
  file_patterns: ["*"]      # Process all file types

folders:
  inbox: "0-QuickNotes"     # Your inbox folder name
  
api_limits:
  claude_model: "claude-sonnet-4-20250514"
  retry_attempts: 3
```

### Prompt Customization

Edit `config/prompts.yaml` to customize how Claude processes your notes:

```yaml
prompts:
  system: |
    You are an AI assistant helping to organize notes...
  user: |
    Please process this note:
    1. Clean up formatting
    2. Add relevant hashtags
    3. Suggest PARA category
    ...
```

## Development

### Project Structure

```
note-assistant/
├── src/                   # Main application code
│   ├── main.py           # Entry point
│   ├── pipeline.py       # Note processing pipeline
│   ├── config.py         # Configuration management
│   ├── google_drive.py   # Google Drive integration
│   ├── claude_client.py  # Claude API client
│   ├── prompt_manager.py # Prompt handling
│   └── utils.py          # Utility functions
├── tests/                # Test suite
├── config/               # Configuration files
├── .github/workflows/    # GitHub Actions
└── requirements.txt      # Dependencies
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_utils.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Add tests first: `tests/test_new_feature.py`
3. Implement feature in `src/`
4. Ensure all tests pass: `python run_tests.py`
5. Update documentation as needed
6. Submit pull request

## Usage

### Manual Processing

For testing or one-off processing:

```bash
# Process notes manually
python run.py

# Check specific configuration
python -c "from src.config import Config; print(Config().inbox_folder)"
```

### Monitoring

GitHub Actions will show processing results:
- Go to your repository → Actions tab
- View recent workflow runs
- Check logs for processing details and any errors

## Troubleshooting

### Common Issues

**"No files found to process"**
- Check that files are in the correct folder (`0-QuickNotes` by default)
- Ensure files aren't already processed (prefixed with `_`)
- Verify Google Drive folder ID is correct

**"Authentication failed"**
- Check that Google Drive credentials are valid
- Ensure the service account has access to your vault folder
- Verify the Anthropic API key is correct

**"Rate limit exceeded"**
- The system will automatically retry with backoff
- Consider reducing `max_notes_per_run` in settings

### Getting Help

1. Check the [GitHub Issues](https://github.com/yourusername/note-assistant/issues)
2. Review GitHub Actions logs for detailed error messages
3. Test locally first to isolate cloud vs. local issues

## Cost Estimation

- **Claude API**: ~$0.01-0.05 per month for typical usage
- **Google Drive**: Free tier sufficient for text files
- **GitHub Actions**: Free tier provides 2000 minutes/month

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Acknowledgments

- Built with [Claude API](https://www.anthropic.com/)
- Inspired by the [PARA Method](https://fortelabs.co/blog/para/)
- Designed for [Obsidian](https://obsidian.md/) users
