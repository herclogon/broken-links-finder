# Broken Link Checker

A Python script that crawls web pages to find broken links with the ability to resume after interruption.

## Features

- **Recursive Web Crawling**: Crawls through web pages up to a specified depth
- **Broken Link Detection**: Identifies links that return HTTP error codes (4xx, 5xx) or fail to connect
- **Resume Capability**: Saves progress to a state file and can continue after interruption
- **Domain Filtering**: Option to restrict crawling to the same domain only
- **Detailed Logging**: Comprehensive logging to both file and console
- **JSON Reports**: Generates detailed reports in JSON format
- **Graceful Interruption**: Handles SIGINT/SIGTERM signals to save state before exiting

## Installation

1. Install Python 3.6 or higher
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```bash
python broken_link_checker.py <start_url>
```

### Advanced Usage
```bash
python broken_link_checker.py <start_url> [max_depth] [same_domain_only]
```

### Parameters

- `start_url`: The URL to start crawling from (required)
  - Must be a valid HTTP or HTTPS URL
  - Example: `https://example.com`

- `max_depth`: Maximum crawling depth (optional, default: 3)
  - Controls how deep the crawler will go from the start URL
  - `0`: Only check the start URL itself
  - `1`: Check start URL + all links found on it
  - `2`: Check start URL + links + links found on those pages
  - `3+`: Continue recursively to specified depth

- `same_domain_only`: Whether to restrict crawling to the same domain (optional, default: true)
  - `true`, `t`, `1`, `yes`, `y`: Only crawl links within the same domain
  - `false`, `f`, `0`, `no`, `n`: Follow links to external domains as well

### Examples

```bash
# Get detailed help
python broken_link_checker.py --help

# Basic crawl of a website (depth 3, same domain only)
python broken_link_checker.py https://example.com

# Shallow crawl with depth 1
python broken_link_checker.py https://example.com 1

# Deep crawl with depth 5, same domain only
python broken_link_checker.py https://example.com 5 true

# Crawl with external domains allowed
python broken_link_checker.py https://example.com 2 false

# Quick check of just the homepage
python broken_link_checker.py https://example.com 0
```

### Help and Validation

The script includes comprehensive argument validation and help:

```bash
# Show detailed help
python broken_link_checker.py --help
python broken_link_checker.py -h

# Error handling for invalid arguments
python broken_link_checker.py                    # Missing URL
python broken_link_checker.py invalid-url        # Invalid URL format
python broken_link_checker.py https://example.com abc  # Invalid depth
python broken_link_checker.py https://example.com 2 maybe  # Invalid boolean
```

## Resume Functionality

The script automatically saves its progress to `crawler_state.json`. If the script is interrupted (Ctrl+C, system shutdown, etc.), you can resume by running the same command again. The script will:

1. Load the previous state from `crawler_state.json`
2. Continue crawling from where it left off
3. Preserve all previously found broken links

## Output Files

The script generates several output files:

- `crawler_state.json`: State file for resume functionality
- `broken_link_checker.log`: Detailed log file
- `broken_links_report_YYYYMMDD_HHMMSS.json`: Final report with all findings

## Report Format

The JSON report contains:

```json
{
  "summary": {
    "start_url": "https://example.com",
    "total_pages_visited": 25,
    "total_broken_links": 3,
    "max_depth": 3,
    "same_domain_only": true,
    "scan_completed": "2025-01-01T12:00:00"
  },
  "broken_links": [
    {
      "url": "https://example.com/broken-page",
      "status": "404 Not Found",
      "found_on": "https://example.com/page1",
      "depth": 2,
      "timestamp": "2025-01-01T12:00:00"
    }
  ],
  "visited_urls": ["https://example.com", "https://example.com/page1", ...]
}
```

## How It Works

1. **Initialization**: Sets up logging, signal handlers, and HTTP session
2. **State Loading**: Attempts to load previous state if available
3. **Crawling**: 
   - Fetches web pages using HTTP requests
   - Extracts all links using BeautifulSoup
   - Validates each link by sending HEAD/GET requests
   - Identifies broken links (4xx, 5xx status codes or connection failures)
4. **State Saving**: Periodically saves progress every 10 pages
5. **Reporting**: Generates comprehensive JSON report at completion

## Configuration

The script uses sensible defaults but can be customized by modifying the `BrokenLinkChecker` class:

- **Timeout**: HTTP request timeout (default: 10-15 seconds)
- **Delay**: Delay between requests (default: 0.5 seconds)
- **User Agent**: Custom user agent string
- **State File**: Custom state file name

## Error Handling

The script handles various error conditions:

- Network timeouts and connection errors
- HTTP errors (4xx, 5xx status codes)
- Invalid URLs and malformed links
- Graceful interruption (Ctrl+C)
- File I/O errors for state saving

## Limitations

- Only crawls HTTP/HTTPS links
- Does not handle JavaScript-generated links
- Respects robots.txt is not implemented (add if needed)
- No authentication support for protected pages

## Performance Considerations

- Uses connection pooling for better performance
- Implements delays between requests to be respectful to servers
- Saves state periodically to minimize data loss
- Uses HEAD requests when possible to reduce bandwidth

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure write permissions for state and log files
2. **Network Errors**: Check internet connection and firewall settings
3. **Memory Usage**: For large sites, consider reducing max_depth
4. **Slow Performance**: Increase delay between requests if servers are rate-limiting

### Debug Mode

For more verbose output, modify the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## License

This script is provided as-is for educational and practical use.
