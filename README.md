# Note Assistant

An AI-powered note processing system that processes raw notes in your Obsidian vault using multiple LLM providers to clean them up, add hashtags, format as bullets, and suggest PARA categorization. Runs locally on your machine with direct file system access.

## Features

- **Local Processing**: Direct access to your Obsidian vault on your file system
- **Multiple LLM Providers**: Support for Claude, OpenAI, Google Gemini, and 100+ other providers via LiteLLM
- **AI Enhancement**: Cleans up and organizes notes with intelligent processing
- **PARA Method Integration**: Suggests categorization for Projects, Areas, Resources, and Archive
- **Recursive Processing**: Process notes in subdirectories within your inbox
- **Note Filtering**: Skip notes marked with `ignoreParse: true` in frontmatter
- **Safe Processing**: Files marked with underscore immediately, reversible operations
- **Flexible Scheduling**: Run manually or set up with cron for automation
- **Automatic Fallback**: Falls back to alternative LLM providers if primary fails
- **Human-Readable Timestamps**: Processed timestamps in "Jan 07, 2025 14:30:25 UTC" format

## How It Works

1. **Capture**: Drop raw thoughts, meeting notes, web clips into your Obsidian vault's `0-QuickNotes` folder (or subdirectories)
2. **Process**: Run the script manually or schedule it with cron to detect new/modified files
3. **Enhance**: LLM cleans up formatting, adds hashtags, creates summaries, and suggests PARA categorization
4. **Review**: Enhanced notes appear in your inbox with metadata for manual sorting

## Architecture

```
Obsidian Vault (Local File System)
├── 0-QuickNotes/          # Raw thought dumps (inbox)
│   ├── meetings/          # Subdirectories are supported
│   ├── ideas/             # Organize raw notes as needed
│   └── *.md               # All text files processed recursively
├── 1-Projects/            # Active projects with deadlines
├── 2-Areas/               # Ongoing responsibilities  
├── 3-Resources/           # Reference materials
└── 4-Archive/             # Inactive items
```

The system adds structured YAML frontmatter to processed notes:

```yaml
---
processed_datetime: "Jan 07, 2025 14:30:25 UTC"
note_hash: "sha256:..."
summary: "Brief one-line summary of the note's main topic"
tags: ["#meeting", "#project-alpha", "#action-items"]
---
```

## Setup

### Prerequisites

- Obsidian vault on your local machine
- Python 3.8 or higher
- API key for your chosen LLM provider (Anthropic, OpenAI, etc.)

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

3. **Get your API key**:
   - For Claude: Sign up at [Anthropic](https://console.anthropic.com/)
   - For OpenAI: Sign up at [OpenAI](https://platform.openai.com/)
   - For other providers: Check [LiteLLM docs](https://docs.litellm.ai/)

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings:
   # ANTHROPIC_API_KEY=your_api_key_here  # For Claude
   # OPENAI_API_KEY=your_api_key_here     # For OpenAI
   # OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
   ```

### Running the Processor

```bash
# Run once to process all notes in inbox
./process_notes.py

# Run tests to verify everything works
./run_tests.py

# For development/debugging
python -m src.main
```

### Automated Processing with Cron

To run automatically every 10 minutes, add this to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path to your installation):
*/10 * * * * cd /path/to/note-assistant && ./process_notes.py >> logs/processing.log 2>&1
```

## Configuration

### LLM Provider Settings

Edit `config/settings.yaml` to configure your LLM providers:

```yaml
# LLM Configuration
llm:
  primary_provider: "litellm"      # Options: "litellm", "claude_direct"
  fallback_provider: "claude_direct"
  
  providers:
    litellm:
      model: "claude-sonnet-4-20250514"  # Can use any LiteLLM-supported model
      # Examples: "gpt-4o", "claude-3-5-sonnet-20241022", "gemini-1.5-pro"
      max_tokens: 8192
      temperature: 0.3
      retry_attempts: 3
      
    claude_direct:
      model: "claude-sonnet-4-20250514"
      max_tokens: 8192
```

### Application Settings

```yaml
processing:
  max_note_size_kb: 10000   # Maximum note size to process
  max_notes_per_run: 10     # Limit notes per run
  file_patterns: ["*.md", "*.txt", "*.org", "*.rst", "*.markdown"]
  recursive: true           # Process subdirectories
  exclude_folders: [".obsidian", ".trash", "templates", ".git"]

folders:
  obsidian_vault_path: ""   # Override vault path (empty = use env variable)
  inbox: "0-QuickNotes"     # Your inbox folder name
```

### Prompt Customization

Edit `config/prompts.yaml` to customize how the LLM processes your notes:

```yaml
prompts:
  system: |
    You are an AI assistant helping to organize notes...
  user: |
    Please process this note:
    1. Clean up formatting
    2. Add relevant hashtags
    3. Create summaries
    ...
```

## 🚨 Critical: Prompt Structure Requirements

**The structure of your prompts in `config/prompts.yaml` is CRITICAL for the system to function properly.** The system expects specific JSON response format from the LLM, and any deviation will cause processing failures.

### Required JSON Response Structure

Your prompts **MUST** instruct the LLM to respond with this exact JSON format:

```json
{
  "content": "enhanced note content here",
  "metadata": {
    "summary": "one line summary",
    "tags": ["#tag1", "#tag2", "#tag3"]
  }
}
```

### Non-Negotiable Requirements

1. **JSON Response**: The LLM must respond with valid JSON (not markdown, not plain text)
2. **"content" field**: Must contain the enhanced note content
3. **"metadata" field**: Must be an object containing at least:
   - **"tags" field**: Must be an array of hashtags (with # prefix)

### Flexible Metadata Fields

While `content` and `tags` are required, you can include additional metadata fields:

```json
{
  "content": "enhanced content",
  "metadata": {
    "summary": "Brief summary",
    "takeaway": "Key insight",
    "tags": ["#required", "#flexible"],
    "para_category": "resources",
    "custom_field": "your custom data"
  }
}
```

### Example Prompt Structure

Here's the critical part of your prompt that ensures proper JSON response:

```yaml
prompts:
  system: |
    You are an AI assistant helping to organize notes.
    
    CRITICAL: Always respond with a JSON object containing:
    - content: The enhanced note content
    - metadata: Object with summary, tags, and other frontmatter
    
  user: |
    Please process this note:
    1. Clean up formatting
    2. Add relevant hashtags
    3. Create summaries
    
    Note content:
    {note_content}
    
    Respond with JSON in this format:
    {
      "content": "enhanced note content here",
      "metadata": {
        "summary": "one line summary",
        "tags": ["#tag1", "#tag2"]
      }
    }
```

### What Happens If Requirements Are Not Met

If your prompt doesn't ensure proper JSON response structure:

- ❌ **Processing fails**: Notes will be marked as failed to process
- ❌ **No enhancement**: Raw notes remain unchanged
- ❌ **Missing metadata**: No tags, summaries, or frontmatter added
- ❌ **System errors**: JSON parsing errors in logs

### Testing Your Prompt Changes

After modifying `config/prompts.yaml`, always test with a sample note:

```bash
# Test with a single note
./process_notes.py

# Check the logs for JSON parsing errors
tail -f logs/processing.log
```

### Common Prompt Mistakes to Avoid

1. **Forgetting JSON instruction**: LLM responds with markdown or plain text
2. **Missing content field**: System can't extract enhanced content
3. **Missing tags field**: No hashtags added to metadata
4. **Inconsistent JSON structure**: Some responses valid, others fail
5. **Complex nested structures**: Keep metadata simple and flat when possible

### Advanced Prompt Features

The current system supports these advanced features in prompts:

```yaml
user: |
  Please process this note:
  1. Clean up formatting and grammar
  2. Add clear bullet points where appropriate
  3. Anywhere you see ((text)), expand these thoughts
  4. If you see any obvious references, create a References section
  5. Generate 3-5 relevant hashtags
  6. Create a one-line summary
  7. Create a one-line takeaway
  
  Note content:
  {note_content}
  
  Respond with JSON in this format:
  {
    "content": "enhanced note content here",
    "metadata": {
      "summary": "one line summary",
      "takeaway": "one line takeaway", 
      "tags": ["#tag1", "#tag2"]
    }
  }
```

Remember: **The JSON response structure is the foundation of the entire system.** All other features depend on this working correctly.

## Advanced Features

### Multiple LLM Provider Support

The system supports 100+ LLM providers through LiteLLM:

```yaml
# Use OpenAI GPT-4
llm:
  providers:
    litellm:
      model: "gpt-4o"
      
# Use Google Gemini
llm:
  providers:
    litellm:
      model: "gemini-1.5-pro"
      
# Use local Ollama
llm:
  providers:
    litellm:
      model: "ollama/llama2"
```

### Skip Processing for Specific Notes

Add `ignoreParse: true` to a note's frontmatter to skip processing:

```yaml
---
ignoreParse: true
---

This note will not be processed by the AI.
```

### Recursive Directory Processing

The system automatically processes notes in subdirectories:

```
0-QuickNotes/
├── daily/
│   └── 2025-01-07.md      # Will be processed
├── meetings/
│   ├── team-standup.md    # Will be processed
│   └── project-review.md  # Will be processed
└── quick-thought.md       # Will be processed
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
│   ├── llm/              # LLM abstraction layer
│   │   ├── base_client.py      # Abstract base class
│   │   ├── litellm_client.py   # LiteLLM implementation
│   │   ├── claude_client_wrapper.py  # Claude wrapper
│   │   └── factory.py          # LLM client factory
│   ├── claude_client.py  # Direct Claude API client
│   ├── prompt_manager.py # Prompt handling
│   ├── note_processor.py # Batch processing coordination
│   └── utils.py          # Utility functions
├── tests/                # Comprehensive test suite
├── config/               # Configuration files
├── process_notes.py      # Main launcher script
└── requirements.txt      # Dependencies
```

### Running Tests

```bash
# Run all tests
./run_tests.py

# Run specific test file
python -m pytest tests/test_llm_abstraction.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Test results: 131 tests, 100% passing
```

### Adding New LLM Providers

1. Implement the `BaseLLMClient` interface
2. Register in `src/llm/factory.py`
3. Add configuration in `settings.yaml`
4. Add tests in `tests/test_llm_abstraction.py`

## Usage

### Manual Processing

For testing or one-off processing:

```bash
# Process notes manually
./process_notes.py

# Check configuration
python -c "from src.config import Config; print(Config().llm)"

# List available LLM providers
python -c "from src.llm import list_available_providers; print(list_available_providers())"
```

### Monitoring

Check the script output and logs:
- Run with verbose output: `./process_notes.py`
- Check log files if using cron: `tail -f logs/processing.log`
- Monitor the `0-QuickNotes` folder for files being processed (prefixed with `_`)

### Example Output

```
2025-07-07 15:09:07,896 - Using LLM provider: litellm/anthropic (claude-sonnet-4-20250514)
2025-07-07 15:09:07,978 - Found 3 eligible files, processing 3
2025-07-07 15:09:07,980 - Note marked to ignore processing (ignoreParse: true): Everything Is Enlightenment.md
2025-07-07 15:09:07,981 - Processing note: Master Vi Quiet.md
2025-07-07 15:09:08,123 - Successfully processed: Master Vi Quiet.md
```

## Troubleshooting

### Common Issues

**"No files found to process"**
- Check that files are in the correct folder (`0-QuickNotes` by default)
- Ensure files aren't already processed (prefixed with `_`)
- Verify the `OBSIDIAN_VAULT_PATH` environment variable points to your vault
- Check that file patterns match your files (`.md`, `.txt`, etc.)

**"max_tokens: X > Y, which is the maximum allowed"**
- Different models have different token limits
- Claude 3.5 Sonnet: 8192 max tokens
- Adjust `max_tokens` in settings.yaml for your model

**"LiteLLM is not installed"**
- Run `pip install litellm` to install LiteLLM
- Or use `claude_direct` provider if you only need Claude

**"Note marked to ignore processing"**
- The note has `ignoreParse: true` in its frontmatter
- Remove this line if you want the note processed

### Getting Help

1. Check the [GitHub Issues](https://github.com/yourusername/note-assistant/issues)
2. Run with verbose logging to see detailed error messages
3. Test the configuration: `python -c "from src.config import Config; c = Config(); print(f'Vault: {c.obsidian_vault_path}')"`

## Cost Estimation

**LLM API Costs** (varies by provider):
- **Claude 3.5 Sonnet**: ~$3/1M input, $15/1M output tokens
- **GPT-4o**: ~$5/1M input, $15/1M output tokens
- **Gemini 1.5 Pro**: ~$1.25/1M input, $5/1M output tokens

**Typical Monthly Usage**:
- Light usage (2-3 short notes/day): ~$0.30-0.50/month
- Moderate usage (5 notes of 400 words/day): ~$1-2/month  
- Heavy usage (10+ notes/day): ~$3-10/month

**Local Processing**: No additional costs (uses your computer's resources)

## Security & Privacy

- All processing happens locally on your machine
- Your notes never leave your computer except for LLM API calls
- API keys are stored in environment variables, not in code
- File operations are atomic and reversible
- Original files are renamed, not deleted

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (131 tests currently)
5. Submit a pull request

## Acknowledgments

- Built with [Claude API](https://www.anthropic.com/) and [LiteLLM](https://github.com/BerriAI/litellm)
- Inspired by the [PARA Method](https://fortelabs.co/blog/para/)
- Designed for [Obsidian](https://obsidian.md/) users

## Changelog

### v2.0.0 (Latest)
- Added support for 100+ LLM providers via LiteLLM
- Implemented automatic fallback between providers
- Added recursive directory processing
- Added `ignoreParse` filter for skipping specific notes
- Changed timestamp format to human-readable
- Improved test coverage to 131 tests (100% passing)

### v1.0.0
- Initial release with Claude API support
- Basic PARA method integration
- Local file system processing