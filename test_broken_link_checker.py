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

import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from collections import deque
import responses
import requests
from datetime import datetime

# Import the module under test
from broken_link_checker import BrokenLinkChecker, main, print_help


class TestBrokenLinkChecker:
    """Test class for BrokenLinkChecker functionality"""
    
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
        checker = BrokenLinkChecker(self.test_url)
        
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
        checker = BrokenLinkChecker(
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
        checker = BrokenLinkChecker(self.test_url, max_depth=2, same_domain_only=False)
        filename = checker._generate_state_filename()
        
        assert "example.com" in filename
        assert "depth2" in filename
        assert "all-domains" in filename
        assert filename.endswith(".json")
        assert filename.startswith("crawler_state_")
    
    def test_normalize_url(self):
        """Test URL normalization"""
        checker = BrokenLinkChecker(self.test_url)
        
        # Test fragment removal
        assert checker.normalize_url("https://example.com/page#section") == "https://example.com/page"
        
        # Test URL without fragment
        assert checker.normalize_url("https://example.com/page") == "https://example.com/page"
        
        # Test empty fragment
        assert checker.normalize_url("https://example.com/page#") == "https://example.com/page"
    
    def test_is_valid_url(self):
        """Test URL validation"""
        checker = BrokenLinkChecker(self.test_url, same_domain_only=True)
        
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
        checker_all_domains = BrokenLinkChecker(self.test_url, same_domain_only=False)
        assert checker_all_domains.is_valid_url("https://other.com/page") == True
    
    @responses.activate
    def test_check_link_status_success(self):
        """Test successful link status checking"""
        checker = BrokenLinkChecker(self.test_url)
        test_link = "https://example.com/test"
        
        responses.add(responses.HEAD, test_link, status=200)
        
        status, reason = checker.check_link_status(test_link)
        assert status == 200
        assert reason is not None
    
    @responses.activate
    def test_check_link_status_not_found(self):
        """Test link status checking for 404 error"""
        checker = BrokenLinkChecker(self.test_url)
        test_link = "https://example.com/notfound"
        
        responses.add(responses.HEAD, test_link, status=404)
        
        status, reason = checker.check_link_status(test_link)
        assert status == 404
        assert reason is not None
    
    @responses.activate
    def test_check_link_status_head_fails_get_succeeds(self):
        """Test fallback to GET when HEAD fails"""
        checker = BrokenLinkChecker(self.test_url)
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
        checker = BrokenLinkChecker(self.test_url)
        test_link = "https://nonexistent.invalid"
        
        status, reason = checker.check_link_status(test_link)
        assert status is None
        assert "error" in reason.lower() or "failed" in reason.lower()
    
    @responses.activate
    def test_extract_links_from_page(self):
        """Test link extraction from HTML page"""
        checker = BrokenLinkChecker(self.test_url)
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
        
        responses.add(responses.GET, test_url, body=html_content, status=200)
        
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
        checker = BrokenLinkChecker(self.test_url, same_domain_only=False)
        test_url = "https://example.com/page"
        
        html_content = """
        <html>
        <body>
            <a href="https://example.com/internal">Internal Link</a>
            <a href="https://other.com/external">External Link</a>
        </body>
        </html>
        """
        
        responses.add(responses.GET, test_url, body=html_content, status=200)
        
        links, status_code = checker.extract_links_from_page(test_url)
        
        assert "https://example.com/internal" in links
        assert "https://other.com/external" in links
    
    def test_extract_links_from_page_request_error(self):
        """Test link extraction when page request fails"""
        checker = BrokenLinkChecker(self.test_url)
        test_url = "https://nonexistent.invalid"
        
        links, status_code = checker.extract_links_from_page(test_url)
        
        assert links == []
        assert status_code is None
    
    def test_save_and_load_state(self):
        """Test state saving and loading"""
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
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
        new_checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
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
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        loaded = checker.load_state()
        assert loaded == False
    
    def test_load_state_invalid_json(self):
        """Test loading state with invalid JSON"""
        # Create invalid JSON file
        with open(self.state_file, 'w') as f:
            f.write("invalid json content")
        
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        loaded = checker.load_state()
        assert loaded == False
    
    @patch('broken_link_checker.BrokenLinkChecker.extract_links_from_page')
    @patch('broken_link_checker.BrokenLinkChecker.check_link_status')
    def test_crawl_page(self, mock_check_status, mock_extract_links):
        """Test crawling a single page"""
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
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
    
    @patch('broken_link_checker.BrokenLinkChecker.extract_links_from_page')
    def test_crawl_page_max_depth_exceeded(self, mock_extract_links):
        """Test that crawling stops at max depth"""
        checker = BrokenLinkChecker(self.test_url, max_depth=1, state_file=self.state_file)
        
        # Try to crawl at depth 2 (exceeds max_depth of 1)
        checker.crawl_page("https://example.com/test", 2)
        
        # Should not have been processed
        assert "https://example.com/test" not in checker.visited_urls
        mock_extract_links.assert_not_called()
    
    @patch('broken_link_checker.BrokenLinkChecker.extract_links_from_page')
    def test_crawl_page_already_visited(self, mock_extract_links):
        """Test that already visited pages are skipped"""
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
        # Mark URL as already visited
        checker.visited_urls.add("https://example.com/test")
        
        # Try to crawl it again
        checker.crawl_page("https://example.com/test", 0)
        
        # Should not have been processed again
        mock_extract_links.assert_not_called()
    
    @patch('broken_link_checker.BrokenLinkChecker.extract_links_from_page')
    def test_crawl_page_failed_to_fetch(self, mock_extract_links):
        """Test handling of pages that fail to fetch"""
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
        # Mock failed page fetch
        mock_extract_links.return_value = ([], None)
        
        # Crawl the page
        checker.crawl_page("https://example.com/test", 0)
        
        # Should be marked as visited and broken
        assert "https://example.com/test" in checker.visited_urls
        assert len(checker.broken_links) == 1
        assert checker.broken_links[0]['url'] == "https://example.com/test"
        assert checker.broken_links[0]['status'] == "Failed to fetch"
    
    @patch('broken_link_checker.BrokenLinkChecker.crawl_page')
    @patch('broken_link_checker.BrokenLinkChecker.load_state')
    @patch('broken_link_checker.BrokenLinkChecker.save_state')
    @patch('broken_link_checker.BrokenLinkChecker.generate_report')
    def test_run_fresh_start(self, mock_report, mock_save, mock_load, mock_crawl):
        """Test running with fresh start (no previous state)"""
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
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
    
    @patch('broken_link_checker.BrokenLinkChecker.crawl_page')
    @patch('broken_link_checker.BrokenLinkChecker.load_state')
    @patch('broken_link_checker.BrokenLinkChecker.save_state')
    @patch('broken_link_checker.BrokenLinkChecker.generate_report')
    def test_run_resume_from_state(self, mock_report, mock_save, mock_load, mock_crawl):
        """Test running with resumed state"""
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
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
        checker = BrokenLinkChecker(self.test_url, state_file=self.state_file)
        
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
    
    @patch('sys.argv', ['broken_link_checker.py', '--help'])
    @patch('sys.exit')
    def test_main_help_flag(self, mock_exit, capsys):
        """Test main function with help flag"""
        main()
        # Should exit with 0 for help
        assert mock_exit.called
        assert 0 in [call[0][0] for call in mock_exit.call_args_list]
        captured = capsys.readouterr()
        assert "Broken Link Checker" in captured.out
    
    @patch('sys.argv', ['broken_link_checker.py'])
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
    
    @patch('sys.argv', ['broken_link_checker.py', 'invalid-url'])
    @patch('sys.exit')
    def test_main_invalid_url(self, mock_exit, capsys):
        """Test main function with invalid URL"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: Invalid URL" in captured.out
    
    @patch('sys.argv', ['broken_link_checker.py', 'https://example.com', 'abc'])
    @patch('sys.exit')
    def test_main_invalid_depth(self, mock_exit, capsys):
        """Test main function with invalid depth"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: max_depth must be a number" in captured.out
    
    @patch('sys.argv', ['broken_link_checker.py', 'https://example.com', '-1'])
    @patch('sys.exit')
    def test_main_negative_depth(self, mock_exit, capsys):
        """Test main function with negative depth"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: max_depth must be 0 or greater" in captured.out
    
    @patch('sys.argv', ['broken_link_checker.py', 'https://example.com', '2', 'maybe'])
    @patch('sys.exit')
    def test_main_invalid_domain_flag(self, mock_exit, capsys):
        """Test main function with invalid domain flag"""
        main()
        mock_exit.assert_called_once_with(1)
        captured = capsys.readouterr()
        assert "ERROR: same_domain_only must be 'true' or 'false'" in captured.out
    
    @patch('sys.argv', ['broken_link_checker.py', 'https://example.com', '2', 'false'])
    @patch('broken_link_checker.BrokenLinkChecker')
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
    
    @patch('sys.argv', ['broken_link_checker.py', 'https://example.com'])
    @patch('broken_link_checker.BrokenLinkChecker')
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
            status=200
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
            status=200
        )
        
        responses.add(responses.GET, "https://example.com/page2", body="<html></html>", status=200)
        responses.add(responses.HEAD, "https://example.com/page1", status=200)
        responses.add(responses.HEAD, "https://example.com/page2", status=200)
        responses.add(responses.HEAD, "https://example.com/broken", status=404)
        responses.add(responses.GET, "https://example.com/broken", status=404)  # Add GET fallback for broken link
        responses.add(responses.HEAD, "https://example.com/subpage", status=200)
        responses.add(responses.GET, "https://example.com/subpage", body="<html></html>", status=200)
        
        # Create checker and run
        checker = BrokenLinkChecker(
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
        assert len(state['broken_links']) == 1
    
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
            status=200
        )
        responses.add(responses.HEAD, "https://example.com/page2", status=200)
        responses.add(responses.GET, "https://example.com/page2", body="<html></html>", status=200)
        
        # Create checker and run (should resume from state)
        checker = BrokenLinkChecker(
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


if __name__ == "__main__":
    pytest.main([__file__])
