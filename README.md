# Broken Links Finder 🔍

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A powerful Python script that crawls web pages to find broken links with intelligent resume capability and comprehensive reporting.

## 🌟 Overview

Broken Links Finder is a robust web crawler designed to help website owners and developers maintain healthy websites by identifying broken links. The tool features intelligent crawling, state persistence, and detailed reporting capabilities.

## Features

- **Recursive Web Crawling**: Crawls through web pages up to a specified depth
- **Broken Link Detection**: Identifies links that return HTTP error codes (4xx, 5xx) or fail to connect
- **Resume Capability**: Saves progress to a state file and can continue after interruption
- **Domain Filtering**: Option to restrict crawling to the same domain only
- **Detailed Logging**: Comprehensive logging to both file and console
- **JSON Reports**: Generates detailed reports in JSON format
- **Graceful Interruption**: Handles SIGINT/SIGTERM signals to save state before exiting

## Installation

### Using uv (Recommended)

1. Install Python 3.7 or higher
2. Install [uv](https://docs.astral.sh/uv/) if you haven't already
3. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

### Basic Usage
```bash
python broken_links_finder.py <start_url>
```

### Advanced Usage
```bash
python broken_links_finder.py <start_url> [max_depth] [same_domain_only]
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
python broken_links_finder.py --help

# Basic crawl of a website (depth 3, same domain only)
python broken_links_finder.py https://example.com

# Shallow crawl with depth 1
python broken_links_finder.py https://example.com 1

# Deep crawl with depth 5, same domain only
python broken_links_finder.py https://example.com 5 true

# Crawl with external domains allowed
python broken_links_finder.py https://example.com 2 false

# Quick check of just the homepage
python broken_links_finder.py https://example.com 0
```

### Help and Validation

The script includes comprehensive argument validation and help:

```bash
# Show detailed help
python broken_links_finder.py --help
python broken_links_finder.py -h

# Error handling for invalid arguments
python broken_links_finder.py                    # Missing URL
python broken_links_finder.py invalid-url        # Invalid URL format
python broken_links_finder.py https://example.com abc  # Invalid depth
python broken_links_finder.py https://example.com 2 maybe  # Invalid boolean
```

## Resume Functionality

The script automatically saves its progress to `crawler_state.json`. If the script is interrupted (Ctrl+C, system shutdown, etc.), you can resume by running the same command again. The script will:

1. Load the previous state from `crawler_state.json`
2. Continue crawling from where it left off
3. Preserve all previously found broken links

## Output Files

The script generates several output files:

- `crawler_state.json`: State file for resume functionality
- `broken_links_finder.log`: Detailed log file
- `broken_links_<domain>_depth<N>_<domain-mode>_<hash>.txt`: Plain text list of broken links
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

The script uses sensible defaults but can be customized by modifying the `BrokenLinksFinder` class:

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

## 🧪 Testing

The project includes a comprehensive test suite. To run tests:

```bash
# Run all tests
python run_tests.py

# Run tests with pytest directly
pytest

# Run tests with coverage
pytest --cov=broken_links_finder
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- How to set up the development environment
- Code style guidelines
- How to submit pull requests
- Reporting bugs and requesting features

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `python run_tests.py`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📋 Requirements

- Python 3.7 or higher
- uv (for dependency management)

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone git@github.com:herclogon/broken-links-finder.git
   cd broken-links-finder
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run your first scan:**
   ```bash
   python broken_links_finder.py https://example.com
   ```
   
   Or with uv:
   ```bash
   uv run python broken_links_finder.py https://example.com
   ```

4. **Check the results:**
   - View the log: `broken_links_finder.log`
   - Check the JSON report: `broken_links_report_*.json`

## 📊 Use Cases

- **Website Maintenance**: Regular health checks for production websites
- **SEO Auditing**: Identify broken links that hurt search rankings
- **Migration Testing**: Verify links after website migrations
- **Quality Assurance**: Automated testing in CI/CD pipelines
- **Content Management**: Maintain link integrity in large content sites

## 🔧 Advanced Configuration

### Custom User Agent
```python
checker = BrokenLinksFinder(start_url)
checker.session.headers.update({'User-Agent': 'Your Custom User Agent'})
```

### Custom Timeouts
```python
# Modify timeout values in the check_link_status method
response = self.session.head(url, timeout=30, allow_redirects=True)
```

### Custom State File Location
```python
checker = BrokenLinksFinder(start_url, state_file='custom_state.json')
```

## 📈 Performance Tips

- **Start Small**: Begin with shallow depths (1-2) for large sites
- **Monitor Resources**: Watch memory usage on very large sites
- **Respect Rate Limits**: Increase delays if you encounter rate limiting
- **Use Resume Feature**: For large scans, use Ctrl+C to pause and resume later

## 🐛 Known Issues

- JavaScript-generated links are not detected
- Some sites may block automated requests
- Very large sites may require significant memory
- Rate limiting may slow down scans on some servers

## 📝 Changelog

### Version 1.0.0
- Initial release
- Basic broken link detection
- Resume functionality
- JSON reporting
- Configurable depth and domain restrictions

## 🙏 Acknowledgments

- Built with [Requests](https://requests.readthedocs.io/) for HTTP handling
- Uses [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- Inspired by the need for reliable website health monitoring

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/herclogon/broken-links-finder/issues) page
2. Read the [Contributing Guide](CONTRIBUTING.md)
3. Create a new issue with detailed information

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Star History

If you find this project useful, please consider giving it a star on GitHub!
