"""Base HTTP client with retry logic and structured logging."""

import time
from typing import Any

import requests

from src.utils.config import DEFAULT_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF_FACTOR
from src.utils.logging_config import get_logger


class APIError(Exception):
    """Base exception for API-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    pass


class BaseClient:
    """Base HTTP client with retry logic, timeout handling, and logging.

    This client provides:
    - Automatic retry with exponential backoff
    - Configurable timeouts
    - Structured logging of requests/responses
    - Rate limit awareness
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """Initialize the base client.

        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_logger(__name__)
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "SMHI-Data-Quality-Monitor/1.0",
        })

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: The current retry attempt number (0 for first retry)

        Returns:
            Delay in seconds before next retry
        """
        return float(RETRY_BACKOFF_FACTOR ** attempt)

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (appended to base_url)
            **kwargs: Additional arguments passed to requests

        Returns:
            Parsed JSON response

        Raises:
            APIError: If request fails after all retries
            RateLimitError: If rate limit is exceeded
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(
                    "Making API request",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                )

                response = self._session.request(method, url, **kwargs)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.logger.warning(
                        "Rate limit exceeded",
                        retry_after=retry_after,
                    )
                    raise RateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after}s",
                        status_code=429,
                    )

                # Raise for other HTTP errors
                response.raise_for_status()

                self.logger.debug(
                    "Request successful",
                    status_code=response.status_code,
                    content_length=len(response.content),
                )

                return response.json()  # type: ignore[no-any-return]

            except requests.exceptions.Timeout as e:
                last_exception = e
                self.logger.warning(
                    "Request timeout",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                self.logger.warning(
                    "Connection error",
                    attempt=attempt + 1,
                    error=str(e),
                )

            except requests.exceptions.HTTPError as e:
                # Don't retry client errors (4xx) except rate limiting
                if e.response is not None and 400 <= e.response.status_code < 500:
                    raise APIError(
                        f"Client error: {e.response.status_code}",
                        status_code=e.response.status_code,
                    ) from e
                last_exception = e
                self.logger.warning(
                    "HTTP error",
                    attempt=attempt + 1,
                    status_code=e.response.status_code if e.response else None,
                )

            except RateLimitError:
                raise

            # Calculate backoff and wait before retry
            if attempt < self.max_retries:
                delay = self._calculate_backoff(attempt)
                self.logger.info(
                    "Retrying request",
                    delay_seconds=delay,
                    next_attempt=attempt + 2,
                )
                time.sleep(delay)

        # All retries exhausted
        raise APIError(
            f"Request failed after {self.max_retries + 1} attempts: {last_exception}",
        ) from last_exception

    def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make a GET request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments passed to requests

        Returns:
            Parsed JSON response
        """
        return self._make_request("GET", endpoint, **kwargs)

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def __enter__(self) -> "BaseClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
