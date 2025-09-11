#!/usr/bin/env python3
"""
Broken Link Checker Script

This script crawls through web pages to find broken links and can resume
after interruption by saving progress to a state file.

Features:
- Crawls web pages recursively
- Checks for broken links (HTTP status codes)
- Saves progress to resume after interruption
- Configurable crawling depth and domains
- Detailed logging and reporting
"""

import requests
import json
import time
import sys
import signal
import os
import hashlib
from urllib.parse import urljoin, urlparse, urldefrag
from bs4 import BeautifulSoup
from collections import deque
import logging
from datetime import datetime
import threading

class BrokenLinksFinder:
    def __init__(self, start_url, max_depth=3, same_domain_only=True, state_file=None):
        self.start_url = start_url
        self.max_depth = max_depth
        self.same_domain_only = same_domain_only

        # Generate unique state file name based on arguments if not provided
        if state_file is None:
            self.state_file = self._generate_state_filename()
        else:
            self.state_file = state_file

        # Initialize state
        self.visited_urls = set()
        self.checked_urls = set()  # Track URLs that have been checked for status
        self.broken_links = []
        self.urls_to_visit = deque()
        self.current_depth = 0
        self.interrupted = False

        # Watchdog timer to prevent hanging
        self.last_activity = time.time()
        self.watchdog_timeout = 300  # 5 minutes timeout

        # Periodic state saving timer
        self.save_timer = None
        self.save_interval = 600  # 10 minutes in seconds
        self.save_lock = threading.Lock()

        # Get domain from start URL
        self.base_domain = urlparse(start_url).netloc

        # Setup logging
        self.setup_logging()

        # Setup signal handler for graceful interruption
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BrokenLinksFinder/1.0)'
        })
    
    def _generate_state_filename(self):
        """Generate a unique state filename based on the argument set"""
        # Create a string representation of the configuration
        config_string = f"{self.start_url}|{self.max_depth}|{self.same_domain_only}"
        
        # Create a hash of the configuration for uniqueness
        config_hash = hashlib.md5(config_string.encode('utf-8')).hexdigest()[:8]
        
        # Extract domain name for readability
        domain = urlparse(self.start_url).netloc.replace('www.', '')
        # Clean domain name for filename (remove invalid characters)
        clean_domain = ''.join(c for c in domain if c.isalnum() or c in '.-').rstrip('.')
        
        # Create descriptive filename
        depth_str = f"depth{self.max_depth}"
        domain_str = "same-domain" if self.same_domain_only else "all-domains"
        
        filename = f"crawler_state_{clean_domain}_{depth_str}_{domain_str}_{config_hash}.json"
        
        return filename
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('broken_links_finder.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Handle interruption signals gracefully"""
        self.logger.info(f"Received signal {signum}. Saving state and exiting...")
        self.interrupted = True
        self.stop_periodic_save()
        self.save_state()
        sys.exit(0)

    def check_watchdog(self):
        """Check if the watchdog timer has expired and show progress"""
        current_time = time.time()
        if current_time - self.last_activity > self.watchdog_timeout:
            self.logger.info(f"Still working... ({len(self.visited_urls)} pages visited, "
                           f"{len(self.broken_links)} broken links found, "
                           f"{len(self.urls_to_visit)} pages remaining)")
            # Reset the watchdog timer to continue monitoring
            self.last_activity = current_time

    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = time.time()

    def start_periodic_save(self):
        """Start the periodic state saving timer"""
        if self.save_timer is not None:
            self.save_timer.cancel()

        self.save_timer = threading.Timer(self.save_interval, self._periodic_save_callback)
        self.save_timer.daemon = True
        self.save_timer.start()
        self.logger.info(f"Periodic state saving started (every {self.save_interval // 60} minutes)")

    def stop_periodic_save(self):
        """Stop the periodic state saving timer"""
        if self.save_timer is not None:
            self.save_timer.cancel()
            self.save_timer = None
            self.logger.info("Periodic state saving stopped")

    def _periodic_save_callback(self):
        """Callback function for periodic state saving"""
        try:
            self.logger.info("Periodic state save triggered")
            self.save_state()
            # Restart the timer for the next interval
            self.start_periodic_save()
        except Exception as e:
            self.logger.error(f"Error during periodic state save: {e}")
            # Still try to restart the timer even if save failed
            self.start_periodic_save()
    
    def save_state(self):
        """Save current crawling state to file"""
        state = {
            'start_url': self.start_url,
            'max_depth': self.max_depth,
            'same_domain_only': self.same_domain_only,
            'visited_urls': list(self.visited_urls),
            'checked_urls': list(self.checked_urls),
            'broken_links': self.broken_links,
            'urls_to_visit': list(self.urls_to_visit),
            'current_depth': self.current_depth,
            'base_domain': self.base_domain,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.logger.info("Starting state save...")
            with self.save_lock:
                with open(self.state_file, 'w') as f:
                    json.dump(state, f)
            self.logger.info(f"State saved to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def load_state(self):
        """Load previous crawling state from file"""
        if not os.path.exists(self.state_file):
            self.logger.info("No previous state file found. Starting fresh.")
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.start_url = state['start_url']
            self.max_depth = state['max_depth']
            self.same_domain_only = state['same_domain_only']
            self.visited_urls = set(state['visited_urls'])
            self.checked_urls = set(state.get('checked_urls', []))  # Use get() for backward compatibility
            self.broken_links = state['broken_links']
            self.urls_to_visit = deque(state['urls_to_visit'])
            self.current_depth = state['current_depth']
            self.base_domain = state['base_domain']
            
            self.logger.info(f"Resumed from state file. Visited: {len(self.visited_urls)}, "
                           f"Checked: {len(self.checked_urls)}, "
                           f"To visit: {len(self.urls_to_visit)}, "
                           f"Broken links found: {len(self.broken_links)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return False
    
    def is_valid_url(self, url):
        """Check if URL is valid for crawling"""
        if not url:
            return False
        
        parsed = urlparse(url)
        
        # Check if it's a valid HTTP/HTTPS URL
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check domain restriction
        if self.same_domain_only and parsed.netloc != self.base_domain:
            return False
        
        return True
    
    def normalize_url(self, url):
        """Normalize URL by removing fragments"""
        return urldefrag(url)[0]
    
    def check_link_status(self, url):
        """Check if a link is broken"""
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            return response.status_code, response.reason
        except requests.exceptions.RequestException:
            # If HEAD fails, try GET with a small range
            try:
                response = self.session.get(url, timeout=10, stream=True)
                return response.status_code, response.reason
            except requests.exceptions.RequestException as e:
                return None, str(e)
    
    def extract_links_from_page(self, url):
        """Extract all links from a web page"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            links = []

            # Find all anchor tags with href
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                normalized_url = self.normalize_url(absolute_url)

                if self.is_valid_url(normalized_url):
                    links.append(normalized_url)

            return links, response.status_code

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return [], None
    
    def crawl_page(self, url, depth):
        """Crawl a single page and check its links"""
        if url in self.visited_urls or depth > self.max_depth:
            return

        self.visited_urls.add(url)
        self.logger.info(f"Crawling (depth {depth}): {url}")

        # Update activity timestamp
        self.update_activity()

        # Extract links from the page
        links, status_code = self.extract_links_from_page(url)

        if status_code is None:
            self.broken_links.append({
                'url': url,
                'status': 'Failed to fetch',
                'found_on': url,
                'depth': depth,
                'timestamp': datetime.now().isoformat()
            })
            self.logger.error(f"Failed to fetch page: {url}")
            return

        self.logger.info(f"Found {len(links)} links on {url}")

        # Check each link
        checked_count = 0
        skipped_count = 0
        for link in links:
            # Update activity timestamp periodically
            if checked_count % 10 == 0:
                self.update_activity()

            # Skip if we've already checked this URL for status
            if link in self.checked_urls:
                skipped_count += 1
                self.logger.debug(f"Skipping already checked URL: {link}")
                # Still add to crawling queue if it's a page we haven't visited
                if link not in self.visited_urls and depth < self.max_depth and self.is_valid_url(link):
                    self.urls_to_visit.append((link, depth + 1))
                continue

            checked_count += 1
            self.logger.info(f"Checking link {checked_count}/{len(links)} (skipped {skipped_count}): {link}")

            # Mark as checked to prevent future duplicate checks
            self.checked_urls.add(link)

            # Check if link is broken
            status_code, reason = self.check_link_status(link)

            if status_code is None or status_code >= 400:
                self.broken_links.append({
                    'url': link,
                    'status': f"{status_code} {reason}" if status_code else reason,
                    'found_on': url,
                    'depth': depth + 1,
                    'timestamp': datetime.now().isoformat()
                })
                self.logger.warning(f"BROKEN LINK: {link} ({status_code} {reason})")
            else:
                self.logger.info(f"OK: {link} ({status_code})")

            # Add to queue for further crawling if within depth limit and not visited
            if link not in self.visited_urls and depth < self.max_depth and self.is_valid_url(link):
                self.urls_to_visit.append((link, depth + 1))

        self.logger.info(f"Completed page {url} - Found {len([l for l in self.broken_links if l['found_on'] == url])} broken links")

        # Save state periodically
        if len(self.visited_urls) % 5 == 0:
            self.logger.info(f"Progress: {len(self.visited_urls)} pages visited, {len(self.broken_links)} broken links found, {len(self.urls_to_visit)} pages remaining")
            self.save_state()
    
    def run(self):
        """Main crawling loop"""
        # Try to load previous state
        if not self.load_state():
            # Start fresh
            self.urls_to_visit.append((self.start_url, 0))

        self.logger.info(f"Starting broken link checker for: {self.start_url}")
        self.logger.info(f"Max depth: {self.max_depth}, Same domain only: {self.same_domain_only}")
        self.logger.info(f"State file: {self.state_file}")

        # Start periodic state saving
        self.start_periodic_save()

        try:
            while self.urls_to_visit and not self.interrupted:
                # Check watchdog timer
                self.check_watchdog()

                url, depth = self.urls_to_visit.popleft()
                self.current_depth = depth

                # Update activity timestamp
                self.update_activity()

                self.crawl_page(url, depth)

                # Small delay to be respectful to servers
                time.sleep(0.5)

            # Final save
            self.save_state()

            # Generate report
            self.generate_report()

        except KeyboardInterrupt:
            self.logger.info("Crawling interrupted by user")
            self.save_state()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.save_state()
            raise
        finally:
            self.stop_periodic_save()
            self.session.close()
    
    def generate_report(self):
        """Generate a detailed report of broken links"""
        report_file = f"broken_links_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'summary': {
                'start_url': self.start_url,
                'total_pages_visited': len(self.visited_urls),
                'total_broken_links': len(self.broken_links),
                'max_depth': self.max_depth,
                'same_domain_only': self.same_domain_only,
                'scan_completed': datetime.now().isoformat()
            },
            'broken_links': self.broken_links,
            'visited_urls': list(self.visited_urls)
        }
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Report generated: {report_file}")
            self.logger.info(f"Summary: {len(self.visited_urls)} pages visited, "
                           f"{len(self.broken_links)} broken links found")
            
            # Print broken links summary
            if self.broken_links:
                self.logger.info("Broken links found:")
                for link in self.broken_links:
                    self.logger.info(f"  - {link['url']} ({link['status']}) found on {link['found_on']}")
            else:
                self.logger.info("No broken links found!")
                
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")


def print_help():
    """Print detailed help information"""
    help_text = """
Broken Link Checker - Find broken links on websites with resume capability

USAGE:
    python broken_links_finder.py <start_url> [max_depth] [same_domain_only]
    python broken_links_finder.py --help

ARGUMENTS:
    start_url           The URL to start crawling from (required)
                       Must be a valid HTTP or HTTPS URL
                       Example: https://example.com

    max_depth          Maximum crawling depth (optional, default: 3)
                       Controls how deep the crawler will go from the start URL
                       - 0: Only check the start URL itself
                       - 1: Check start URL + all links found on it
                       - 2: Check start URL + links + links found on those pages
                       - 3+: Continue recursively to specified depth
                       Example: 2

    same_domain_only   Whether to restrict crawling to the same domain (optional, default: true)
                       - true: Only crawl links within the same domain as start_url
                       - false: Follow links to external domains as well
                       Example: false

EXAMPLES:
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

RESUME FUNCTIONALITY:
    The script automatically saves progress to a unique state file based on your arguments
    State files are named: crawler_state_<domain>_depth<N>_<domain-mode>_<hash>.json
    If interrupted (Ctrl+C), run the same command to resume from where it stopped
    Different argument sets will use different state files, allowing parallel crawls

OUTPUT FILES:
    - crawler_state_<domain>_depth<N>_<domain-mode>_<hash>.json: State file for resume functionality
    - broken_links_finder.log: Detailed log file
    - broken_links_report_YYYYMMDD_HHMMSS.json: Final report

INTERRUPTION:
    Press Ctrl+C to gracefully stop and save progress
    The script will save current state and can be resumed later

REQUIREMENTS:
    Install dependencies: pip install -r requirements.txt
    """
    print(help_text)


def main():
    """Main function to run the broken link checker"""
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)
    
    if len(sys.argv) < 2:
        print("ERROR: Missing required argument <start_url>")
        print("\nUsage: python broken_links_finder.py <start_url> [max_depth] [same_domain_only]")
        print("       python broken_links_finder.py --help")
        print("\nExample: python broken_links_finder.py https://example.com 2 true")
        print("\nFor detailed help, run: python broken_links_finder.py --help")
        sys.exit(1)
    
    start_url = sys.argv[1]
    
    # Validate URL format
    if not start_url.startswith(('http://', 'https://')):
        print(f"ERROR: Invalid URL '{start_url}'. URL must start with http:// or https://")
        print("Example: https://example.com")
        sys.exit(1)
    
    # Parse max_depth with validation
    max_depth = 3  # default
    if len(sys.argv) > 2:
        try:
            max_depth = int(sys.argv[2])
            if max_depth < 0:
                print("ERROR: max_depth must be 0 or greater")
                sys.exit(1)
        except ValueError:
            print(f"ERROR: max_depth must be a number, got '{sys.argv[2]}'")
            print("Example: python broken_links_finder.py https://example.com 2")
            sys.exit(1)
    
    # Parse same_domain_only with validation
    same_domain_only = True  # default
    if len(sys.argv) > 3:
        domain_arg = sys.argv[3].lower()
        if domain_arg in ['true', 't', '1', 'yes', 'y']:
            same_domain_only = True
        elif domain_arg in ['false', 'f', '0', 'no', 'n']:
            same_domain_only = False
        else:
            print(f"ERROR: same_domain_only must be 'true' or 'false', got '{sys.argv[3]}'")
            print("Example: python broken_links_finder.py https://example.com 2 false")
            sys.exit(1)
    
    print(f"Starting broken link checker with:")
    print(f"  URL: {start_url}")
    print(f"  Max depth: {max_depth}")
    print(f"  Same domain only: {same_domain_only}")
    print(f"  Press Ctrl+C to stop and save progress")
    print("-" * 50)
    
    checker = BrokenLinksFinder(start_url, max_depth, same_domain_only)
    checker.run()


if __name__ == "__main__":
    main()
