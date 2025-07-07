# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI-powered note processing system that processes raw notes in your Obsidian vault using Claude API to clean them up, add hashtags, format as bullets, and suggest PARA categorization. Runs locally with direct file system access.

## Project Architecture

### Technology Stack
- **Language**: Python 3.x
- **AI Processing**: Claude API (Anthropic)
- **File System**: Local file system operations
- **Automation**: Local script with optional cron scheduling
- **Note System**: Obsidian with PARA method organization

### Directory Structure
```
note-assistant/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point for local processing
│   ├── pipeline.py             # NotePipeline class with all processing stages
│   ├── note_processor.py       # Orchestrates batch processing
│   ├── prompt_manager.py       # Claude prompts and note formatting logic
│   ├── file_system.py          # Local file system operations
│   ├── claude_client.py        # Claude API communication wrapper
│   ├── config.py              # Configuration management
│   └── utils.py                # Hashing, YAML frontmatter utilities
├── tests/
│   └── test_*.py               # Unit tests
├── config/
│   ├── prompts.yaml           # Claude prompts configuration
│   └── settings.yaml          # App settings (limits, patterns)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── process_notes.py           # Main launcher script
└── README.md
```

### Key Components

1. **Note Detection**: Scans `0-QuickNotes/` folder, filters for text files only
2. **State Management**: Files marked with underscore immediately upon processing start
3. **Claude Processing**: Sends raw notes to Claude API for enhancement
4. **File Management**: Renames processed files with underscore prefix
5. **Metadata Addition**: Adds standardized YAML frontmatter

### YAML Frontmatter Specification

All processed notes will have this exact YAML frontmatter structure:

```yaml
---
processed_datetime: "Jan 07, 2025 14:30:00 UTC"  # Human-readable format
note_hash: "sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
summary: "Brief one-line summary of the note's main topic"
tags: ["#meeting", "#project-alpha", "#action-items"]  # Array of hashtags
---
```

#### Field Definitions:
- **processed_datetime**: When the note was processed (human-readable UTC timestamp)
- **note_hash**: SHA-256 hash of the note content (excluding frontmatter)
- **summary**: AI-generated one-sentence summary
- **tags**: Array of relevant hashtags (always prefixed with #)

### Processing Pipeline Architecture

The processing pipeline is implemented as a single `NotePipeline` class with methods for each stage:

```python
class NotePipeline:
    def __init__(self, drive_client, claude_client, config):
        self.drive = drive_client
        self.claude = claude_client
        self.config = config
    
    def process_note(self, note):
        """Main pipeline execution"""
        if not self._filter(note):
            return
        
        if not self._validate(note):
            return
            
        self._mark_as_processing(note)
        enhanced = self._enhance_with_claude(note)
        metadata = self._generate_metadata(enhanced)
        self._save_to_drive(note, enhanced, metadata)
    
    def _filter(self, note):
        """Skip underscore files, check hashes, filter by file type"""
        
    def _validate(self, note):
        """Check file size and format limits"""
        
    def _mark_as_processing(self, note):
        """Rename with underscore prefix"""
        
    def _enhance_with_claude(self, note):
        """Send to Claude for processing"""
        
    def _generate_metadata(self, enhanced):
        """Create YAML frontmatter"""
        
    def _save_to_drive(self, note, enhanced, metadata):
        """Save processed note back to Drive"""
```

This design keeps all pipeline logic in one place since most stages are simple operations (5-20 lines each). The shared context (config, clients) is easily accessible, and the flow is clear and testable.

### Module Responsibilities

- **main.py**: Entry point, initializes services and handles global errors
- **pipeline.py**: NotePipeline class containing all processing stages as methods
- **note_processor.py**: Coordinates batch processing and pipeline execution
- **prompt_manager.py**:
  - Loads prompts from config/prompts.yaml
  - Formats notes for Claude input
  - Manages prompt versioning
- **google_drive.py**: 
  - Service account authentication
  - File operations (list, read, write, rename)
  - Handles Google Drive API specifics
- **claude_client.py**:
  - Anthropic API communication
  - Retry logic and rate limiting
  - Response streaming for large notes
- **config.py**:
  - Loads settings from config/settings.yaml
  - Manages environment variables
  - Provides configuration to all modules
- **utils.py**:
  - SHA-256 file hashing
  - YAML frontmatter parsing/generation
  - Common utility functions

## Development Commands

```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run locally (for testing)
python src/main.py

# Lint code
flake8 src/ tests/

# Format code
black src/ tests/
```

## Configuration Files

### Environment Variables (.env)
Create a `.env` file (never commit this) with:
```
ANTHROPIC_API_KEY=your_claude_api_key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### Application Settings (config/settings.yaml)
```yaml
processing:
  max_note_size_kb: 100  # Maximum note size in KB
  max_notes_per_run: 10  # Maximum notes to process per run
  file_patterns: ["*.md", "*.txt", "*.org", "*.rst", "*.markdown"]  # Only process text files
  
folders:
  obsidian_vault_path: ""  # Override vault path (empty = use env variable)
  inbox: "0-QuickNotes"
  para:
    projects: "1-Projects"
    areas: "2-Areas"
    resources: "3-Resources"
    archive: "4-Archive"

api_limits:
  claude_max_tokens: 4096
  claude_model: "claude-3-opus-20240229"
  retry_attempts: 3
  retry_delay_seconds: 2
```

### Prompt Configuration (config/prompts.yaml)
```yaml
version: "1.0"
prompts:
  system: |
    You are an AI assistant helping to organize and enhance notes for a PARA method system.
    Your task is to clean up raw notes, add relevant hashtags, and suggest categorization.
    
  user: |
    Please process this note:
    1. Clean up formatting and grammar
    2. Convert to clear bullet points where appropriate
    3. Generate 3-5 relevant hashtags
    4. Suggest PARA category (projects/areas/resources/archive)
    5. Create a one-line summary
    
    Note content:
    {note_content}
```

## Running the Application

### Manual Execution
```bash
# Run once to process all eligible notes
python process_notes.py

# Run for development/testing
python src/main.py
```

### Automated Processing with Cron
Add to crontab for automatic processing:
```bash
# Run every 10 minutes
*/10 * * * * cd /path/to/note-assistant && python process_notes.py >> logs/processing.log 2>&1
```

## API Integration Patterns

### Claude API Usage
- **Prompt Management** (via prompt_manager.py):
  - Keep prompts in separate module for easy updates
  - Use system prompts for consistent behavior
  - Include examples in prompts for better output
  - Version prompts for A/B testing
- **API Communication** (via claude_client.py):
  - Use streaming for longer notes
  - Implement retry logic with exponential backoff
  - Monitor token usage to stay within budget
  - Handle rate limits gracefully

### File System Integration
- Direct access to local Obsidian vault
- File type filtering via glob patterns (only text files processed)
- Atomic file operations for safety
- Backup creation before processing
- Proper file permission handling
- Cross-platform path handling

## Testing Strategy

1. **Unit Tests**: Test individual components (hashing, YAML parsing, etc.)
2. **Integration Tests**: Test cloud storage and Claude API interactions with mocks
3. **Prompt Testing**: Test prompt_manager with various note formats and edge cases
4. **End-to-End Tests**: Test full workflow with sample notes

## Security Considerations

- Never commit API keys or credentials
- Use GitHub repository secrets for sensitive data
- Implement rate limiting to prevent API abuse
- Log errors without exposing sensitive information