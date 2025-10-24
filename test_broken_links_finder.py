#!/usr/bin/env python3
"""
Comprehensive test suite for the Broken Link Checker

This test suite covers:
- Unit tests for all major methods
- Integration tests for the complete workflow
- Mock tests for HTTP requests
- State management tests
- Error handling tests
"""

import json
import os
import shutil
import tempfile
from collections import deque
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
import responses

# Import the module under test
from broken_links_finder import BrokenLinksFinder, main, print_help
from validate_broken_links_report import (
    PageSourceCollector,
    parse_report,
    validate_entries,
    write_validated_report,
)


class TestBrokenLinksFinder:
    """Test class for BrokenLinksFinder functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.test_url = "https://example.com"
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        
    def teardown_method(self):
        """Clean up after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_default_parameters(self):
        """Test initialization with default parameters"""
        checker = BrokenLinksFinder(self.test_url)
        
        assert checker.start_url == self.test_url
        assert checker.max_depth == 3
        assert checker.same_domain_only == True
        assert checker.base_domain == "example.com"
        assert isinstance(checker.visited_urls, set)
        assert isinstance(checker.broken_links, list)
        assert isinstance(checker.urls_to_visit, deque)
        assert checker.current_depth == 0
        assert checker.interrupted == False
    
    def test_init_custom_parameters(self):
        """Test initialization with custom parameters"""
        checker = BrokenLinksFinder(
            self.test_url, 
            max_depth=5, 
            same_domain_only=False,
            state_file=self.state_file
        )
        
        assert checker.max_depth == 5
        assert checker.same_domain_only == False
        assert checker.state_file == self.state_file
    
    def test_generate_state_filename(self):
        """Test state filename generation"""
        checker = BrokenLinksFinder(self.test_url, max_depth=2, same_domain_only=False)
        filename = checker._generate_state_filename()
        
        assert "example.com" in filename
        assert "depth2" in filename
        assert "all-domains" in filename
        assert filename.endswith(".json")
        assert filename.startswith("crawler_state_")

    def test_generate_broken_links_filename(self):
        """Ensure broken links report uses the plain text extension"""
        checker = BrokenLinksFinder(self.test_url, max_depth=4, same_domain_only=True)
        filename = checker._generate_broken_links_filename()

        assert "example.com" in filename
        assert "depth4" in filename
        assert "same-domain" in filename
        assert filename.startswith("broken_links_")
        assert filename.endswith(".txt")
    
    def test_normalize_url(self):
        """Test URL normalization"""
        checker = BrokenLinksFinder(self.test_url)
        
        # Test fragment removal
        assert checker.normalize_url("https://example.com/page#section") == "https://example.com/page"
        
        # Test URL without fragment
        assert checker.normalize_url("https://example.com/page") == "https://example.com/page"
        
        # Test empty fragment
        assert checker.normalize_url("https://example.com/page#") == "https://example.com/page"
    
    def test_is_valid_url(self):
        """Test URL validation"""
        checker = BrokenLinksFinder(self.test_url, same_domain_only=True)
        
        # Valid URLs
        assert checker.is_valid_url("https://example.com/page") == True
        assert checker.is_valid_url("http://example.com/page") == True
        
        # Invalid URLs
        assert checker.is_valid_url("") == False
        assert checker.is_valid_url("ftp://example.com") == False
        assert checker.is_valid_url("mailto:test@example.com") == False
        assert checker.is_valid_url("javascript:void(0)") == False
        
        # Domain restrictions
        assert checker.is_valid_url("https://other.com/page") == False
        
        # Test with same_domain_only=False
        checker_all_domains = BrokenLinksFinder(self.test_url, same_domain_only=False)
        assert checker_all_domains.is_valid_url("https://other.com/page") == True
    
    @responses.activate
    def test_check_link_status_success(self):
        """Test successful link status checking"""
        checker = BrokenLinksFinder(self.test_url)
        test_link = "https://example.com/test"
        
        responses.add(responses.HEAD, test_link, status=200)
        
        status, reason = checker.check_link_status(test_link)
        assert status == 200
        assert reason is not None
    
    @responses.activate
    def test_check_link_status_not_found(self):
        """Test link status checking for 404 error"""
        checker = BrokenLinksFinder(self.test_url)
        test_link = "https://example.com/notfound"
        
        responses.add(responses.HEAD, test_link, status=404)
        
        status, reason = checker.check_link_status(test_link)
        assert status == 404
        assert reason is not None
    
    @responses.activate
    def test_check_link_status_head_fails_get_succeeds(self):
        """Test fallback to GET when HEAD fails"""
        checker = BrokenLinksFinder(self.test_url)
        test_link = "https://example.com/test"
        
        # HEAD request fails
        responses.add(responses.HEAD, test_link, body=requests.exceptions.RequestException())
        # GET request succeeds
        responses.add(responses.GET, test_link, status=200)
        
        status, reason = checker.check_link_status(test_link)
        assert status == 200
        assert reason is not None
    
    def test_check_link_status_connection_error(self):
        """Test link status checking with connection error"""
        checker = BrokenLinksFinder(self.test_url)
        test_link = "https://nonexistent.invalid"
        
        status, reason = checker.check_link_status(test_link)
        assert status is None
        assert "error" in reason.lower() or "failed" in reason.lower()
    
    @responses.activate
    def test_extract_links_from_page(self):
        """Test link extraction from HTML page"""
        checker = BrokenLinksFinder(self.test_url)
        test_url = "https://example.com/page"
        
        html_content = """
        <html>
        <body>
            <a href="/relative">Relative Link</a>
            <a href="https://example.com/absolute">Absolute Link</a>
            <a href="https://other.com/external">External Link</a>
            <a href="#fragment">Fragment Link</a>
            <a href="mailto:test@example.com">Email Link</a>
            <a>No href</a>
        </body>
        </html>
        """
        
        responses.add(
            responses.GET,
            test_url,
            body=html_content,
            status=200,
            headers={"Content-Type": "text/html"},
        )
        
        links, status_code = checker.extract_links_from_page(test_url)
        
        assert status_code == 200
        assert "https://example.com/relative" in links
        assert "https://example.com/absolute" in links
        # External link should not be included when same_domain_only=True
        assert "https://other.com/external" not in links
        # Fragment and mailto links should not be included
        assert len([l for l in links if "fragment" in l]) == 0
        assert len([l for l in links if "mailto" in l]) == 0
    
    @responses.activate
    def test_extract_links_from_page_with_external_domains(self):
        """Test link extraction with external domains allowed"""
        checker = BrokenLinksFinder(self.test_url, same_domain_only=False)
        test_url = "https://example.com/page"
        
        html_content = """
        <html>
        <body>
            <a href="https://example.com/internal">Internal Link</a>
            <a href="https://other.com/external">External Link</a>
        </body>
        </html>
        """
        
        responses.add(
            responses.GET,
            test_url,
            body=html_content,
            status=200,
            headers={"Content-Type": "text/html"},
        )
        
        links, status_code = checker.extract_links_from_page(test_url)
        
        assert "https://example.com/internal" in links
        assert "https://other.com/external" in links
    
    def test_extract_links_from_page_request_error(self):
        """Test link extraction when page request fails"""
        checker = BrokenLinksFinder(self.test_url)
        test_url = "https://nonexistent.invalid"

        links, status_code = checker.extract_links_from_page(test_url)

        assert links == []
        assert status_code is None

    @responses.activate
    def test_extract_links_from_non_html_page(self):
        """Test that non-HTML pages are skipped"""
        checker = BrokenLinksFinder(self.test_url)
        test_url = "https://example.com/document.pdf"

        # Mock response with PDF content type
        responses.add(
            responses.GET,
            test_url,
            body=b"PDF content here",
            status=200,
            headers={'content-type': 'application/pdf'}
        )

        links, status_code = checker.extract_links_from_page(test_url)

        assert links == []  # Should return empty list for non-HTML content
        assert status_code == 200  # Status should still be returned

    @responses.activate
    def test_extract_links_from_video_page(self):
        """Test that video files are skipped"""
        checker = BrokenLinksFinder(self.test_url)
        test_url = "https://example.com/video.mp4"

        # Mock response with video content type
        responses.add(
            responses.GET,
            test_url,
            body=b"video content",
            status=200,
            headers={'content-type': 'video/mp4'}
        )

        links, status_code = checker.extract_links_from_page(test_url)

        assert links == []  # Should return empty list for video content
        assert status_code == 200
    
    def test_save_and_load_state(self):
        """Test state saving and loading"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Set up some state
        checker.visited_urls.add("https://example.com/page1")
        checker.visited_urls.add("https://example.com/page2")
        checker.broken_links.append({
            'url': 'https://example.com/broken',
            'status': '404 Not Found',
            'found_on': 'https://example.com/page1',
            'depth': 1,
            'timestamp': datetime.now().isoformat()
        })
        checker.urls_to_visit.append(("https://example.com/page3", 1))
        checker.current_depth = 1
        
        # Save state
        checker.save_state()
        assert os.path.exists(self.state_file)
        
        # Create new checker and load state
        new_checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        loaded = new_checker.load_state()
        
        assert loaded == True
        assert len(new_checker.visited_urls) == 2
        assert "https://example.com/page1" in new_checker.visited_urls
        assert "https://example.com/page2" in new_checker.visited_urls
        assert len(new_checker.broken_links) == 1
        assert new_checker.broken_links[0]['url'] == 'https://example.com/broken'
        assert len(new_checker.urls_to_visit) == 1
        # URLs to visit are loaded as lists from JSON, then converted back to tuples
        url_item = new_checker.urls_to_visit[0]
        if isinstance(url_item, list):
            url_item = tuple(url_item)
        assert url_item == ("https://example.com/page3", 1)
        assert new_checker.current_depth == 1
    
    def test_load_state_no_file(self):
        """Test loading state when no file exists"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        loaded = checker.load_state()
        assert loaded == False
    
    def test_load_state_invalid_json(self):
        """Test loading state with invalid JSON"""
        # Create invalid JSON file
        with open(self.state_file, 'w') as f:
            f.write("invalid json content")
        
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        loaded = checker.load_state()
        assert loaded == False
    
    @patch('broken_links_finder.BrokenLinksFinder.extract_links_from_page')
    @patch('broken_links_finder.BrokenLinksFinder.check_link_status')
    def test_crawl_page(self, mock_check_status, mock_extract_links):
        """Test crawling a single page"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Mock the methods
        mock_extract_links.return_value = (
            ["https://example.com/link1", "https://example.com/link2"], 
            200
        )
        mock_check_status.side_effect = [(200, "OK"), (404, "Not Found")]
        
        # Crawl the page
        checker.crawl_page("https://example.com/test", 0)
        
        # Verify results
        assert "https://example.com/test" in checker.visited_urls
        assert len(checker.broken_links) == 1
        assert checker.broken_links[0]['url'] == "https://example.com/link2"
        assert checker.broken_links[0]['status'] == "404 Not Found"
        assert len(checker.urls_to_visit) == 2  # Both links added for further crawling
    
    @patch('broken_links_finder.BrokenLinksFinder.extract_links_from_page')
    def test_crawl_page_max_depth_exceeded(self, mock_extract_links):
        """Test that crawling stops at max depth"""
        checker = BrokenLinksFinder(self.test_url, max_depth=1, state_file=self.state_file)
        
        # Try to crawl at depth 2 (exceeds max_depth of 1)
        checker.crawl_page("https://example.com/test", 2)
        
        # Should not have been processed
        assert "https://example.com/test" not in checker.visited_urls
        mock_extract_links.assert_not_called()
    
    @patch('broken_links_finder.BrokenLinksFinder.extract_links_from_page')
    def test_crawl_page_already_visited(self, mock_extract_links):
        """Test that already visited pages are skipped"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Mark URL as already visited
        checker.visited_urls.add("https://example.com/test")
        
        # Try to crawl it again
        checker.crawl_page("https://example.com/test", 0)
        
        # Should not have been processed again
        mock_extract_links.assert_not_called()
    
    @patch('broken_links_finder.BrokenLinksFinder.extract_links_from_page')
    def test_crawl_page_failed_to_fetch(self, mock_extract_links):
        """Test handling of pages that fail to fetch"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Mock failed page fetch
        mock_extract_links.return_value = ([], None)
        
        # Crawl the page
        checker.crawl_page("https://example.com/test", 0)
        
        # Should be marked as visited and broken
        assert "https://example.com/test" in checker.visited_urls
        assert len(checker.broken_links) == 1
        assert checker.broken_links[0]['url'] == "https://example.com/test"
        assert checker.broken_links[0]['status'] == "Failed to fetch"
    
    @patch('broken_links_finder.BrokenLinksFinder.crawl_page')
    @patch('broken_links_finder.BrokenLinksFinder.load_state')
    @patch('broken_links_finder.BrokenLinksFinder.save_state')
    @patch('broken_links_finder.BrokenLinksFinder.generate_report')
    def test_run_fresh_start(self, mock_report, mock_save, mock_load, mock_crawl):
        """Test running with fresh start (no previous state)"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Mock no previous state
        mock_load.return_value = False
        
        # Mock crawl_page to prevent infinite loop
        def mock_crawl_side_effect(url, depth):
            checker.urls_to_visit.clear()  # Clear queue to end loop
        
        mock_crawl.side_effect = mock_crawl_side_effect
        
        # Run the checker
        checker.run()
        
        # Verify behavior
        mock_load.assert_called_once()
        mock_crawl.assert_called_once_with(self.test_url, 0)
        mock_save.assert_called()
        mock_report.assert_called_once()
    
    @patch('broken_links_finder.BrokenLinksFinder.crawl_page')
    @patch('broken_links_finder.BrokenLinksFinder.load_state')
    @patch('broken_links_finder.BrokenLinksFinder.save_state')
    @patch('broken_links_finder.BrokenLinksFinder.generate_report')
    def test_run_resume_from_state(self, mock_report, mock_save, mock_load, mock_crawl):
        """Test running with resumed state"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Mock previous state exists
        mock_load.return_value = True
        checker.urls_to_visit.append(("https://example.com/resume", 1))
        
        # Mock crawl_page to prevent infinite loop
        def mock_crawl_side_effect(url, depth):
            checker.urls_to_visit.clear()  # Clear queue to end loop
        
        mock_crawl.side_effect = mock_crawl_side_effect
        
        # Run the checker
        checker.run()
        
        # Verify behavior
        mock_load.assert_called_once()
        mock_crawl.assert_called_once_with("https://example.com/resume", 1)
        mock_save.assert_called()
        mock_report.assert_called_once()
    
    def test_generate_report(self):
        """Test report generation"""
        checker = BrokenLinksFinder(self.test_url, state_file=self.state_file)
        
        # Set up some data
        checker.visited_urls.add("https://example.com/page1")
        checker.visited_urls.add("https://example.com/page2")
        checker.broken_links.append({
            'url': 'https://example.com/broken',
            'status': '404 Not Found',
            'found_on': 'https://example.com/page1',
            'depth': 1,
            'timestamp': datetime.now().isoformat()
        })
        
        # Generate report
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            checker.generate_report()
            
            # Verify file was opened for writing
            mock_open.assert_called_once()
            # Verify JSON was written
            mock_file.write.assert_called()
            
            # Get the written content
            written_calls = mock_file.write.call_args_list
            written_content = ''.join(call[0][0] for call in written_calls)
            
            # Parse and verify the JSON structure
            report_data = json.loads(written_content)
            assert 'summary' in report_data
            assert 'broken_links' in report_data
            assert 'visited_urls' in report_data
            assert report_data['summary']['total_pages_visited'] == 2
            assert report_data['summary']['total_broken_links'] == 1
            assert len(report_data['broken_links']) == 1
            assert len(report_data['visited_urls']) == 2


class TestMainFunction:
    """Test class for main function and CLI interface"""
    
    def test_print_help(self, capsys):
        """Test help printing"""
        print_help()
        captured = capsys.readouterr()
        assert "Broken Link Checker" in captured.out
        assert "USAGE:" in captured.out
        assert "EXAMPLES:" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', '--help'])
    @patch('sys.exit')
    def test_main_help_flag(self, mock_exit, capsys):
        """Test main function with help flag"""
        main()
        # Should exit with 0 for help
        assert mock_exit.called
        assert 0 in [call[0][0] for call in mock_exit.call_args_list]
        captured = capsys.readouterr()
        assert "Broken Link Checker" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py'])
    @patch('sys.exit')
    def test_main_missing_url(self, mock_exit, capsys):
        """Test main function with missing URL argument"""
        try:
            main()
        except IndexError:
            # This is expected when sys.argv doesn't have enough arguments
            pass
        captured = capsys.readouterr()
        assert "ERROR: Missing required argument" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', 'invalid-url'])
    @patch('sys.exit')
    def test_main_invalid_url(self, mock_exit, capsys):
        """Test main function with invalid URL"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: Invalid URL" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', 'https://example.com', 'abc'])
    @patch('sys.exit')
    def test_main_invalid_depth(self, mock_exit, capsys):
        """Test main function with invalid depth"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: max_depth must be a number" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', 'https://example.com', '-1'])
    @patch('sys.exit')
    def test_main_negative_depth(self, mock_exit, capsys):
        """Test main function with negative depth"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: max_depth must be 0 or greater" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', 'https://example.com', '2', 'maybe'])
    @patch('sys.exit')
    def test_main_invalid_domain_flag(self, mock_exit, capsys):
        """Test main function with invalid domain flag"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: same_domain_only must be 'true' or 'false'" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', 'https://example.com', '2', 'false'])
    @patch('broken_links_finder.BrokenLinksFinder')
    def test_main_valid_arguments(self, mock_checker_class, capsys):
        """Test main function with valid arguments"""
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker
        
        main()
        
        # Verify checker was created with correct arguments
        mock_checker_class.assert_called_once_with('https://example.com', 2, False)
        mock_checker.run.assert_called_once()
        
        captured = capsys.readouterr()
        assert "Starting broken link checker with:" in captured.out
        assert "URL: https://example.com" in captured.out
        assert "Max depth: 2" in captured.out
        assert "Same domain only: False" in captured.out
    
    @patch('sys.argv', ['broken_links_finder.py', 'https://example.com'])
    @patch('broken_links_finder.BrokenLinksFinder')
    def test_main_default_arguments(self, mock_checker_class):
        """Test main function with default arguments"""
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker
        
        main()
        
        # Verify checker was created with default arguments
        mock_checker_class.assert_called_once_with('https://example.com', 3, True)
        mock_checker.run.assert_called_once()


class TestIntegration:
    """Integration tests for the complete workflow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "integration_test_state.json")
    
    def teardown_method(self):
        """Clean up after tests"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @responses.activate
    def test_complete_crawl_workflow(self):
        """Test complete crawling workflow with mocked HTTP responses"""
        # Set up mock responses
        responses.add(
            responses.GET,
            "https://example.com",
            body="""
            <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="/broken">Broken Link</a>
            </body>
            </html>
            """,
            status=200,
            headers={"Content-Type": "text/html"},
        )
        
        responses.add(
            responses.GET,
            "https://example.com/page1",
            body="""
            <html>
            <body>
                <a href="/subpage">Subpage</a>
            </body>
            </html>
            """,
            status=200,
            headers={"Content-Type": "text/html"},
        )
        
        responses.add(
            responses.GET,
            "https://example.com/page2",
            body="<html></html>",
            status=200,
            headers={"Content-Type": "text/html"},
        )
        responses.add(responses.HEAD, "https://example.com/page1", status=200)
        responses.add(responses.HEAD, "https://example.com/page2", status=200)
        responses.add(responses.HEAD, "https://example.com/broken", status=404)
        responses.add(responses.GET, "https://example.com/broken", status=404)  # Add GET fallback for broken link
        responses.add(responses.HEAD, "https://example.com/subpage", status=200)
        responses.add(
            responses.GET,
            "https://example.com/subpage",
            body="<html></html>",
            status=200,
            headers={"Content-Type": "text/html"},
        )
        
        # Create checker and run
        checker = BrokenLinksFinder(
            "https://example.com", 
            max_depth=2, 
            state_file=self.state_file
        )
        
        # Mock the delay to speed up test
        with patch('time.sleep'):
            checker.run()
        
        # Verify results
        assert len(checker.visited_urls) >= 3  # At least main page, page1, page2
        # Should have at least 1 broken link (the broken link may be detected multiple times)
        assert len(checker.broken_links) >= 1
        # Check that the broken link is detected
        broken_urls = [link['url'] for link in checker.broken_links]
        assert "https://example.com/broken" in broken_urls
        
        # Verify state file was created
        assert os.path.exists(self.state_file)
        
        # Verify state file content
        with open(self.state_file, 'r') as f:
            state = json.load(f)
        assert state['start_url'] == "https://example.com"
        assert state['max_depth'] == 2
        assert len(state['visited_urls']) >= 3
        # The broken link might be detected multiple times (as link and as page)
        assert len(state['broken_links']) >= 1
        # Verify the broken link is in the results
        broken_urls = [link['url'] for link in state['broken_links']]
        assert "https://example.com/broken" in broken_urls
    
    @responses.activate
    def test_resume_functionality(self):
        """Test resume functionality with state file"""
        # Create initial state
        initial_state = {
            'start_url': 'https://example.com',
            'max_depth': 2,
            'same_domain_only': True,
            'visited_urls': ['https://example.com'],
            'broken_links': [],
            'urls_to_visit': [['https://example.com/page1', 1]],
            'current_depth': 1,
            'base_domain': 'example.com',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(initial_state, f)
        
        # Set up mock response for the remaining page
        responses.add(
            responses.GET,
            "https://example.com/page1",
            body="""
            <html>
            <body>
                <a href="/page2">Page 2</a>
            </body>
            </html>
            """,
            status=200,
            headers={"Content-Type": "text/html"},
        )
        responses.add(responses.HEAD, "https://example.com/page2", status=200)
        responses.add(
            responses.GET,
            "https://example.com/page2",
            body="<html></html>",
            status=200,
            headers={"Content-Type": "text/html"},
        )
        
        # Create checker and run (should resume from state)
        checker = BrokenLinksFinder(
            "https://example.com", 
            max_depth=2, 
            state_file=self.state_file
        )
        
        with patch('time.sleep'):
            checker.run()
        
        # Verify it resumed correctly
        assert "https://example.com" in checker.visited_urls  # From loaded state
        assert "https://example.com/page1" in checker.visited_urls  # Newly crawled
        assert len(checker.visited_urls) >= 2


class TestReportValidation:
    """Tests for the report validation utility."""

    def test_parse_report_extracts_entries(self, tmp_path):
        """Ensure the validator can parse formatted report files."""
        report_content = "\n".join(
            [
                "Broken Links Report",
                "Start URL: https://example.com",
                "--------------------------------------------------",
                "Broken Link: https://example.com/missing",
                "Status: 404 Not Found",
                "Found On: https://example.com",
                "Depth: 2",
                "Timestamp: 2024-01-01T00:00:00",
                "------------------------------",
                "Broken Link: https://example.com/other",
                "Status: Failed to fetch",
                "Found On: https://example.com/page",
                "",
            ]
        )

        report_path = tmp_path / "report.txt"
        report_path.write_text(report_content, encoding="utf-8")

        header, entries = parse_report(str(report_path))

        assert header[0] == "Broken Links Report"
        assert len(entries) == 2
        assert entries[0]["broken_link"] == "https://example.com/missing"
        assert entries[0]["depth"] == 2
        assert entries[1]["status"] == "Failed to fetch"

    @responses.activate
    def test_validate_entries_rechecks_404(self):
        """Validate that only 404 entries are rechecked and results tallied."""
        entries = [
            {"broken_link": "https://example.com/missing", "status": "404 Not Found"},
            {"broken_link": "https://example.com/skip", "status": "Failed to fetch"},
        ]

        responses.add(responses.HEAD, "https://example.com/missing", status=404)
        responses.add(responses.GET, "https://example.com/missing", status=200)

        session = requests.Session()
        validated, summary = validate_entries(entries, session, timeout=5.0, delay=0.0)

        assert summary["rechecked"] == 1
        assert summary["resolved"] == 1
        assert summary["still_broken"] == 0
        assert summary["duplicates_skipped"] == 0
        assert validated[0]["validation"]["outcome"] == "resolved"
        assert validated[0]["validation"]["method"] == "GET"
        assert validated[1]["validation"]["outcome"] == "skipped"
        assert validated[1]["validation"]["checked"] is False

    @responses.activate
    def test_validate_entries_collects_source_snapshot(self, tmp_path):
        """Capture page source when the broken link remains unresolved."""
        entries = [
            {
                "broken_link": "https://example.com/missing",
                "status": "404 Not Found",
                "found_on": "https://example.com/page",
            }
        ]

        responses.add(responses.HEAD, "https://example.com/missing", status=404)
        responses.add(responses.GET, "https://example.com/missing", status=404)
        responses.add(
            responses.GET,
            "https://example.com/page",
            status=200,
            body='<html><body><a href="https://example.com/missing">Broken</a></body></html>',
            content_type="text/html",
        )

        session = requests.Session()
        collector = PageSourceCollector(
            session, str(tmp_path), timeout=5.0, verbose=False
        )

        validated, summary = validate_entries(
            entries,
            session,
            timeout=5.0,
            delay=0.0,
            source_collector=collector,
        )

        assert summary["still_broken"] == 1
        assert summary["link_removed"] == 0
        assert summary["duplicates_skipped"] == 0
        source_path = validated[0]["validation"].get("source_path")
        assert source_path is not None
        saved_file = Path(source_path)
        assert saved_file.exists()
        assert "Broken" in saved_file.read_text(encoding="utf-8")
        assert validated[0]["validation"]["reference_found"] is True

    @responses.activate
    def test_validate_entries_marks_removed_when_link_missing(self):
        """Mark links as removed when the source page no longer references them."""
        entries = [
            {
                "broken_link": "https://example.com/missing",
                "status": "404 Not Found",
                "found_on": "https://example.com/page",
            }
        ]

        responses.add(responses.HEAD, "https://example.com/missing", status=404)
        responses.add(responses.GET, "https://example.com/missing", status=404)
        responses.add(
            responses.GET,
            "https://example.com/page",
            status=200,
            body="<html><body>No link here</body></html>",
            content_type="text/html",
        )

        session = requests.Session()
        validated, summary = validate_entries(entries, session, timeout=5.0, delay=0.0)

        assert summary["link_removed"] == 1
        assert summary["still_broken"] == 0
        assert validated[0]["validation"]["outcome"] == "link_removed"
        assert validated[0]["validation"]["reference_found"] is False

    @responses.activate
    def test_validate_entries_skips_duplicates_by_found_on(self):
        """Ensure duplicate entries with the same source page are skipped."""
        entries = [
            {
                "broken_link": "https://example.com/missing",
                "status": "404 Not Found",
                "found_on": "https://example.com/page",
            },
            {
                "broken_link": "https://example.com/missing",
                "status": "404 Not Found",
                "found_on": "https://example.com/page",
            },
        ]

        responses.add(responses.HEAD, "https://example.com/missing", status=404)
        responses.add(responses.GET, "https://example.com/missing", status=404)
        responses.add(
            responses.GET,
            "https://example.com/page",
            status=200,
            body='<html><body><a href="/missing">Broken</a></body></html>',
            content_type="text/html",
        )

        session = requests.Session()
        validated, summary = validate_entries(entries, session, timeout=5.0, delay=0.0)

        assert summary["duplicates_skipped"] == 1
        assert summary["total_entries"] == 1
        assert summary["link_removed"] == 0
        assert len(validated) == 1
        assert validated[0]["broken_link"] == "https://example.com/missing"

    @responses.activate
    def test_validate_entries_verbose_output(self, capsys):
        """Ensure verbose flag surfaces progress information."""
        entries = [{"broken_link": "https://example.com/missing", "status": "404 Not Found"}]

        responses.add(responses.HEAD, "https://example.com/missing", status=404)
        responses.add(responses.GET, "https://example.com/missing", status=404)

        session = requests.Session()
        validate_entries(entries, session, timeout=5.0, delay=0.0, verbose=True)

        captured = capsys.readouterr()
        assert "[1/1] Rechecking https://example.com/missing" in captured.out
        assert "Validation complete:" in captured.out

    def test_write_validated_report_outputs_summary(self, tmp_path):
        """Check that the writer emits a readable validation summary."""
        header = ["Broken Links Report"]
        captured_path = tmp_path / "source.html"
        validated_entries = [
            {
                "broken_link": "https://example.com/missing",
                "status": "404 Not Found",
                "validation": {
                    "checked": True,
                    "outcome": "still_broken",
                    "status_text": "404 Not Found",
                    "method": "GET",
                    "timestamp": "2024-01-01T00:00:00+00:00",
                    "source_path": str(captured_path),
                },
            },
            {
                "broken_link": "https://example.com/fixed",
                "status": "404 Not Found",
                "validation": {
                    "checked": True,
                    "outcome": "resolved",
                    "status_text": "200 OK",
                    "method": "GET",
                    "timestamp": "2024-01-01T00:00:01+00:00",
                },
            },
        ]
        summary = {
            "validated_at": "2024-01-01T00:00:00+00:00",
            "source_report": "/tmp/report.txt",
            "total_entries": 2,
            "rechecked": 2,
            "duplicates_skipped": 0,
            "link_removed": 0,
            "still_broken": 1,
            "resolved": 1,
            "other_error": 0,
            "errors": 0,
        }

        output_path = tmp_path / "validated.txt"
        write_validated_report(str(output_path), header, validated_entries, summary)

        content = output_path.read_text(encoding="utf-8")
        assert "Validation Summary" in content
        assert "Still Broken: 1" in content
        assert "Broken Link: https://example.com/missing" in content
        assert "Validation Outcome: Still Broken" in content
        assert "Duplicates Skipped: 0" in content
        assert "Links Removed: 0" in content
        assert f"Source Saved To: {captured_path.name}" in content
        assert "https://example.com/fixed" not in content

    def test_write_validated_report_no_still_broken(self, tmp_path):
        """When no links remain broken, emit a helpful message."""
        header = ["Broken Links Report"]
        validated_entries = [
            {
                "broken_link": "https://example.com/fixed",
                "status": "404 Not Found",
                "validation": {
                    "checked": True,
                    "outcome": "resolved",
                    "status_text": "200 OK",
                    "method": "GET",
                    "timestamp": "2024-01-01T00:00:01+00:00",
                },
            }
        ]
        summary = {
            "validated_at": "2024-01-01T00:00:00+00:00",
            "source_report": "/tmp/report.txt",
            "total_entries": 1,
            "rechecked": 1,
            "duplicates_skipped": 0,
            "link_removed": 0,
            "still_broken": 0,
            "resolved": 1,
            "other_error": 0,
            "errors": 0,
        }

        output_path = tmp_path / "validated.txt"
        write_validated_report(str(output_path), header, validated_entries, summary)
        content = output_path.read_text(encoding="utf-8")
        assert "No links remain broken after validation." in content
        assert "Duplicates Skipped: 0" in content
        assert "Links Removed: 0" in content
        assert "https://example.com/fixed" not in content

    def test_write_validated_report_reports_removed_links(self, tmp_path):
        """Ensure removed links are reflected in the summary but omitted from details."""
        header = ["Broken Links Report"]
        validated_entries = [
            {
                "broken_link": "https://example.com/removed",
                "status": "404 Not Found",
                "validation": {
                    "checked": True,
                    "outcome": "link_removed",
                    "status_text": "404 Not Found",
                    "method": "GET",
                    "timestamp": "2024-01-01T00:00:02+00:00",
                    "reference_found": False,
                },
            }
        ]
        summary = {
            "validated_at": "2024-01-01T00:00:02+00:00",
            "source_report": "/tmp/report.txt",
            "total_entries": 1,
            "rechecked": 1,
            "duplicates_skipped": 0,
            "link_removed": 1,
            "still_broken": 0,
            "resolved": 0,
            "other_error": 0,
            "errors": 0,
        }

        output_path = tmp_path / "validated_removed.txt"
        write_validated_report(str(output_path), header, validated_entries, summary)
        content = output_path.read_text(encoding="utf-8")
        assert "Links Removed: 1" in content
        assert "No links remain broken after validation." in content
        assert "https://example.com/removed" not in content


if __name__ == "__main__":
    pytest.main([__file__])
