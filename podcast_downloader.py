#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Podcast Downloader
Extracted from gPodder (https://gpodder.github.io/)

This module provides robust podcast/media file downloading with:
- Resume capability (HTTP Range headers)
- Automatic retry on network errors
- Proper User-Agent identification
- HTTP authentication support
- Proxy support (HTTP, SOCKS5, SOCKS5h)
- Content-disposition filename extraction

Original gPodder code: Copyright (c) 2005-2018 The gPodder Team
Licensed under GNU General Public License v3+

ContentRange class: Copyright (c) 2007 Ian Bicking and Contributors (MIT License)
"""

import email
import email.utils
import logging
import os
import platform
import sys
import urllib.error
from typing import Optional, Callable, Tuple, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, RequestException
from urllib3.util.retry import Retry

__version__ = '1.0.0'
__url__ = 'https://github.com/gpodder/gpodder'

logger = logging.getLogger(__name__)

# Constants
REDIRECT_RETRIES = 3
DEFAULT_TIMEOUT = 60
DEFAULT_USER_AGENT = f'PodcastDownloader/{__version__} (+{__url__}) {platform.system()}'


class ContentRange:
    """Represents the Content-Range header.

    This header is ``start-stop/length``, where stop and length can be
    ``*`` (represented as None in the attributes).

    Based on: http://svn.pythonpaste.org/Paste/WebOb/trunk/webob/byterange.py
    Copyright (c) 2007 Ian Bicking and Contributors
    Licensed under MIT License
    """

    def __init__(self, start: int, stop: Optional[int], length: Optional[int]):
        assert start >= 0, f"Bad start: {start!r}"
        assert stop is None or (stop >= 0 and stop >= start), f"Bad stop: {stop!r}"
        self.start = start
        self.stop = stop
        self.length = length

    def __repr__(self):
        return f'<{self.__class__.__name__} {self}>'

    def __str__(self):
        stop = '*' if self.stop is None else self.stop + 1
        length = '*' if self.length is None else self.length
        return f'bytes {self.start}-{stop}/{length}'

    def __iter__(self):
        """Iterate through a ContentRange.

        Mostly so you can unpack this, like:
            start, stop, length = content_range
        """
        return iter([self.start, self.stop, self.length])

    @classmethod
    def parse(cls, value: Optional[str]) -> Optional['ContentRange']:
        """Parse the Content-Range header. Returns None if it cannot parse."""
        if value is None:
            return None

        value = value.strip()
        if not value.startswith('bytes '):
            return None

        value = value[len('bytes '):].strip()
        if '/' not in value:
            return None

        startstop, length = value.split('/', 1)
        if '-' not in startstop:
            return None

        start, end = startstop.split('-', 1)
        try:
            start = int(start)
            end = None if end == '*' else int(end)
            length = None if length == '*' else int(length)
        except ValueError:
            return None

        if end is None:
            return cls(start, None, length)
        else:
            return cls(start, end - 1, length)


class DownloadError(Exception):
    """Base exception for download errors."""
    pass


class DownloadHTTPError(DownloadError):
    """HTTP error during download."""

    def __init__(self, url: str, status_code: int, message: str):
        self.url = url
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code} for {url}: {message}")


class DownloadCancelled(DownloadError):
    """Download was cancelled by user."""
    pass


class PodcastDownloader:
    """Robust podcast/media file downloader with resume capability.

    Features:
    - Automatic resume from partial downloads
    - Configurable retry strategy
    - Custom User-Agent
    - HTTP authentication
    - Proxy support
    - Progress callbacks

    Example:
        downloader = PodcastDownloader(
            user_agent='MyPodcastApp/1.0',
            max_retries=3
        )

        def progress(count, block_size, total_size):
            percent = 100 * count * block_size / total_size
            print(f"Progress: {percent:.1f}%")

        headers, real_url = downloader.download(
            url='https://example.com/podcast.mp3',
            filename='podcast.mp3',
            progress_callback=progress
        )
    """

    # URL escaping for malformed URLs (RFC2396 Section 2.4.3)
    ESCAPE_CHARS = {ord(c): f'%{ord(c):x}' for c in ' <>#"{}|\\^[]`'}

    def __init__(
        self,
        user_agent: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = DEFAULT_TIMEOUT,
        proxy: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None
    ):
        """Initialize the podcast downloader.

        Args:
            user_agent: Custom User-Agent string (default: auto-generated)
            max_retries: Number of retries on network errors (default: 3)
            timeout: Socket timeout in seconds (default: 60)
            proxy: Proxy configuration dict, e.g. {'http': 'socks5h://localhost:9050'}
            auth: HTTP authentication tuple (username, password)
        """
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.max_retries = max_retries
        self.timeout = timeout
        self.proxy = proxy
        self.auth = auth

    def _init_session(self) -> requests.Session:
        """Initialize a requests session with retry strategy."""
        retry_strategy = Retry(
            total=self.max_retries + REDIRECT_RETRIES,
            connect=self.max_retries,
            read=self.max_retries,
            redirect=max(REDIRECT_RETRIES, self.max_retries),
            status=self.max_retries,
            status_forcelist=Retry.RETRY_AFTER_STATUS_CODES.union((408, 418, 504, 598, 599,))
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def download(
        self,
        url: str,
        filename: str,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        auth: Optional[Tuple[str, str]] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Download a file with automatic resume capability.

        Args:
            url: URL to download
            filename: Local filename to save to
            progress_callback: Optional callback(count, block_size, total_size)
            auth: Optional HTTP authentication (overrides instance auth)

        Returns:
            Tuple of (response_headers, real_url)

        Raises:
            DownloadHTTPError: HTTP error occurred
            DownloadError: Other download error
        """
        return self._retrieve_resume(url, filename, progress_callback, auth=auth)

    def _retrieve_resume(
        self,
        url: str,
        filename: str,
        reporthook: Optional[Callable[[int, int, int], None]] = None,
        auth: Optional[Tuple[str, str]] = None,
        disable_auth: bool = False
    ) -> Tuple[Dict[str, Any], str]:
        """Download files from a URL with resume support.

        Resumes a download if the local filename exists and
        the server supports download resuming.

        Based on gPodder's DownloadURLOpener.retrieve_resume()
        """
        current_size = 0
        tfp = None
        headers = {'User-agent': self.user_agent}

        # Use provided auth or instance auth
        if not disable_auth:
            auth = auth or self.auth
        else:
            auth = None

        # Check if we can resume
        if os.path.exists(filename):
            try:
                current_size = os.path.getsize(filename)
                tfp = open(filename, 'ab')
                # If the file exists, then only download the remainder
                if current_size > 0:
                    headers['Range'] = f'bytes={current_size}-'
                    logger.info(f"Resuming download from byte {current_size}")
            except Exception:
                logger.warning(f'Cannot resume download: {filename}', exc_info=True)
                tfp = None
                current_size = 0

        if tfp is None:
            tfp = open(filename, 'wb')

        # Fix problematic URLs (spaces, special characters not properly encoded)
        url = url.translate(self.ESCAPE_CHARS)

        session = self._init_session()
        logger.debug(f"Downloading: {url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Proxy: {self.proxy}")

        try:
            with session.get(
                url,
                headers=headers,
                stream=True,
                auth=auth,
                proxies=self.proxy,
                timeout=self.timeout
            ) as resp:
                try:
                    resp.raise_for_status()
                except HTTPError as e:
                    if auth is not None:
                        # Try again without authentication (some servers advertise
                        # auth but actually serve content without it - bug 1296)
                        tfp.close()
                        logger.info("Retrying without authentication")
                        return self._retrieve_resume(url, filename, reporthook, auth=None, disable_auth=True)
                    else:
                        raise DownloadHTTPError(url, resp.status_code, str(e))

                response_headers = dict(resp.headers)

                # Validate resume capability
                if current_size > 0:
                    # We told the server to resume - see if it agrees
                    # See RFC2616 (206 Partial Content + Section 14.16)
                    conrange = ContentRange.parse(response_headers.get('content-range', ''))
                    if conrange is None or conrange.start != current_size:
                        # Server doesn't support resume properly, restart from beginning
                        logger.warning('Cannot resume: Invalid Content-Range (RFC2616). Restarting download.')
                        tfp.close()
                        tfp = open(filename, 'wb')
                        current_size = 0

                result = response_headers, resp.url
                block_size = 1024 * 8
                size = -1
                read = current_size
                blocknum = current_size // block_size

                if reporthook:
                    if "content-length" in response_headers:
                        size = int(response_headers['content-length']) + current_size
                    reporthook(blocknum, block_size, size)

                # Download the file
                for block in resp.iter_content(block_size):
                    read += len(block)
                    tfp.write(block)
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, block_size, size)

                tfp.close()
                del tfp

            # Raise exception if actual size does not match content-length header
            if size >= 0 and read < size:
                raise urllib.error.ContentTooShortError(
                    f"retrieval incomplete: got only {read} out of {size} bytes",
                    result
                )

            logger.info(f"Download complete: {filename} ({read} bytes)")
            return result

        except Exception:
            if tfp:
                tfp.close()
            raise


def get_header_param(headers: Dict[str, str], param: str, header_name: str) -> Optional[str]:
    """Extract a parameter from an HTTP header.

    Uses the email module to retrieve parameters from HTTP headers.
    This can be used to get the "filename" parameter of the
    "content-disposition" header for downloads.

    Args:
        headers: Dictionary of HTTP headers
        param: Parameter name to extract (e.g., 'filename')
        header_name: Header name to search (e.g., 'content-disposition')

    Returns:
        Parameter value or None if not found

    Example:
        headers = {'content-disposition': 'attachment; filename="episode.mp3"'}
        filename = get_header_param(headers, 'filename', 'content-disposition')
        # Returns: 'episode.mp3'
    """
    value = None
    try:
        headers_string = [f'{k}:{v}' for k, v in headers.items()]
        msg = email.message_from_string('\n'.join(headers_string))
        if header_name in msg:
            raw_value = msg.get_param(param, header=header_name)
            if raw_value is not None:
                value = email.utils.collapse_rfc2231_value(raw_value)
    except Exception:
        logger.error(f'Cannot get {param} from {header_name}', exc_info=True)

    return value


def simple_download(
    url: str,
    filename: str,
    user_agent: Optional[str] = None,
    progress: bool = True
) -> str:
    """Simple interface for downloading a podcast/media file.

    Args:
        url: URL to download
        filename: Local filename to save to
        user_agent: Optional custom User-Agent
        progress: Show progress output (default: True)

    Returns:
        Path to downloaded file

    Example:
        simple_download(
            'https://example.com/podcast.mp3',
            'episode.mp3'
        )
    """
    downloader = PodcastDownloader(user_agent=user_agent)

    def progress_callback(count, block_size, total_size):
        if not progress or total_size < 0:
            return
        percent = min(100.0, 100.0 * count * block_size / total_size)
        downloaded = count * block_size
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(f'\rDownload: {percent:5.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)', end='', flush=True)

    try:
        headers, real_url = downloader.download(url, filename, progress_callback if progress else None)
        if progress:
            print()  # New line after progress

        # Try to get better filename from headers
        better_filename = get_header_param(headers, 'filename', 'content-disposition')
        if better_filename and better_filename != os.path.basename(filename):
            logger.info(f"Server suggested filename: {better_filename}")

        return filename
    except DownloadError as e:
        logger.error(f"Download failed: {e}")
        raise


def main():
    """Command-line interface for podcast downloader."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download podcasts/media files with resume capability'
    )
    parser.add_argument('url', help='URL to download')
    parser.add_argument('filename', nargs='?', help='Output filename (optional, derived from URL if not provided)')
    parser.add_argument('--user-agent', '-u', help='Custom User-Agent string')
    parser.add_argument('--auth', '-a', metavar='USER:PASS', help='HTTP authentication (username:password)')
    parser.add_argument('--proxy', '-p', help='Proxy URL (e.g., socks5h://localhost:9050)')
    parser.add_argument('--retries', '-r', type=int, default=3, help='Max retries (default: 3)')
    parser.add_argument('--timeout', '-t', type=int, default=60, help='Timeout in seconds (default: 60)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress progress output')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Determine filename
    if not args.filename:
        args.filename = os.path.basename(args.url.split('?')[0])
        if not args.filename:
            args.filename = 'downloaded_file'

    # Parse authentication
    auth = None
    if args.auth:
        if ':' in args.auth:
            auth = tuple(args.auth.split(':', 1))
        else:
            print("Error: --auth must be in format username:password", file=sys.stderr)
            return 1

    # Parse proxy
    proxy = None
    if args.proxy:
        proxy = {'http': args.proxy, 'https': args.proxy}

    try:
        downloader = PodcastDownloader(
            user_agent=args.user_agent,
            max_retries=args.retries,
            timeout=args.timeout,
            proxy=proxy,
            auth=auth
        )

        def progress_callback(count, block_size, total_size):
            if args.quiet or total_size < 0:
                return
            percent = min(100.0, 100.0 * count * block_size / total_size)
            downloaded = count * block_size
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f'\rProgress: {percent:5.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)', end='', flush=True)

        headers, real_url = downloader.download(
            args.url,
            args.filename,
            progress_callback if not args.quiet else None
        )

        if not args.quiet:
            print()  # New line after progress
            print(f"✓ Download complete: {args.filename}")

            # Show filename from headers if different
            better_filename = get_header_param(headers, 'filename', 'content-disposition')
            if better_filename and better_filename != os.path.basename(args.filename):
                print(f"  Server suggested filename: {better_filename}")

        return 0

    except DownloadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDownload cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
