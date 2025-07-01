# Note Assistant

An AI-powered note processing system that processes raw notes in your Obsidian vault using Claude API to clean them up, add hashtags, format as bullets, and suggest PARA categorization. Runs locally on your machine with direct file system access.

## Features

- **Local Processing**: Direct access to your Obsidian vault on your file system
- **AI Enhancement**: Uses Claude API to clean up and organize notes
- **PARA Method Integration**: Suggests categorization for Projects, Areas, Resources, and Archive
- **Multi-modal Support**: Processes text files, images, and other media
- **Safe Processing**: Files marked with underscore immediately, reversible operations
- **Flexible Scheduling**: Run manually or set up with cron for automation

## How It Works

1. **Capture**: Drop raw thoughts, meeting notes, web clips into your Obsidian vault's `0-QuickNotes` folder
2. **Process**: Run the script manually or schedule it with cron to detect new/modified files
3. **Enhance**: Claude AI cleans up formatting, adds hashtags, creates summaries, and suggests PARA categorization
4. **Review**: Enhanced notes appear in your inbox with metadata for manual sorting

## Architecture

```
Obsidian Vault (Local File System)
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

- Obsidian vault on your local machine
- Python 3.8 or higher
- Anthropic API key

### Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/yourusername/note-assistant.git
   cd note-assistant
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Get your Anthropic API key**:
   - Sign up at [Anthropic](https://console.anthropic.com/)
   - Create an API key

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings:
   # ANTHROPIC_API_KEY=your_api_key_here
   # OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
   ```

### Running the Processor

```bash
# Run once to process all notes in inbox
python process_notes.py

# Run tests to verify everything works
python run_tests.py

# For development/debugging
python src/main.py
```

### Automated Processing with Cron

To run automatically every 10 minutes, add this to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path to your installation):
*/10 * * * * cd /path/to/note-assistant && python process_notes.py >> logs/processing.log 2>&1
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
  obsidian_vault_path: ""   # Override vault path (empty = use env variable)
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
│   ├── file_system.py    # Local file system operations
│   ├── claude_client.py  # Claude API client
│   ├── prompt_manager.py # Prompt handling
│   ├── note_processor.py # Batch processing coordination
│   └── utils.py          # Utility functions
├── tests/                # Test suite
├── config/               # Configuration files
├── process_notes.py      # Main launcher script
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
python process_notes.py

# Check specific configuration
python -c "from src.config import Config; print(Config().inbox_folder)"
```

### Monitoring

Check the script output and logs:
- Run with verbose output: `python process_notes.py`
- Check log files if using cron: `tail -f logs/processing.log`
- Monitor the `0-QuickNotes` folder for files being processed (prefixed with `_`)

## Troubleshooting

### Common Issues

**"No files found to process"**
- Check that files are in the correct folder (`0-QuickNotes` by default)
- Ensure files aren't already processed (prefixed with `_`)
- Verify the `OBSIDIAN_VAULT_PATH` environment variable points to your vault

**"Vault path does not exist"**
- Check that the path in `OBSIDIAN_VAULT_PATH` is correct
- Ensure the path is absolute, not relative
- Verify you have read/write permissions to the vault directory

**"Authentication failed"**
- Verify the Anthropic API key is correct
- Check that you have sufficient credits in your Anthropic account

**"Rate limit exceeded"**
- The system will automatically retry with backoff
- Consider reducing `max_notes_per_run` in settings

### Getting Help

1. Check the [GitHub Issues](https://github.com/yourusername/note-assistant/issues)
2. Run with verbose logging to see detailed error messages
3. Test the configuration: `python -c "from src.config import Config; c = Config(); print(f'Vault: {c.obsidian_vault_path}')"`

## Cost Estimation

- **Claude API**: ~$0.01-0.05 per month for typical usage
- **Local Processing**: No additional costs (uses your computer's resources)

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
