"""URL Security Manager enforcing URL normalization, scheme validation, and dangerous scheme rejection."""

from urllib.parse import urlparse

from app.tools.models.errors import ToolErrorCode, ToolExecutionError

ALLOWED_URL_SCHEMES: set[str] = {"http", "https"}
REJECTED_URL_SCHEMES: set[str] = {
    "javascript",
    "data",
    "vbscript",
    "file",
    "about",
    "chrome",
}


class UrlSecurityManager:
    """Manager validating and sanitizing URLs for safe browser navigation."""

    def __init__(self, allowed_schemes: set[str] | None = None) -> None:
        self.allowed_schemes = allowed_schemes or ALLOWED_URL_SCHEMES

    def sanitize_url(self, raw_url: str) -> str:
        """Sanitize and normalize a raw URL input string."""
        url_str = raw_url.strip()
        if not url_str:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="URL string cannot be empty.",
            )

        # Detect scheme if present (e.g. 'javascript:', 'data:', 'file:')
        if ":" in url_str:
            scheme_candidate = url_str.split(":", 1)[0].lower().strip()
            if scheme_candidate in REJECTED_URL_SCHEMES:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.PERMISSION_DENIED,
                    message=f"URL Security Policy Violation: Dangerous scheme '{scheme_candidate}:' is strictly prohibited.",
                )
            if "://" in url_str and scheme_candidate not in self.allowed_schemes:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.INVALID_INPUT,
                    message=f"URL Security Policy Violation: Unsupported scheme '{scheme_candidate}:'. Allowed schemes: {list(self.allowed_schemes)}",
                )

        # Prepend https:// if no scheme is specified (e.g. 'youtube.com' -> 'https://youtube.com')
        if "://" not in url_str:
            url_str = "https://" + url_str

        try:
            parsed = urlparse(url_str)
            scheme = parsed.scheme.lower()

            if scheme in REJECTED_URL_SCHEMES:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.PERMISSION_DENIED,
                    message=f"URL Security Policy Violation: Dangerous scheme '{scheme}:' is strictly prohibited.",
                )

            if scheme not in self.allowed_schemes:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.INVALID_INPUT,
                    message=f"URL Security Policy Violation: Unsupported scheme '{scheme}:'. Allowed schemes: {list(self.allowed_schemes)}",
                )

            if not parsed.netloc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.INVALID_INPUT,
                    message=f"Malformed URL string '{raw_url}': Missing domain hostname.",
                )

            return url_str
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Failed to parse URL string '{raw_url}': {exc}",
            ) from exc

    def is_safe_url(self, raw_url: str) -> bool:
        """Check if URL passes security policy without raising exceptions."""
        try:
            self.sanitize_url(raw_url)
            return True
        except ToolExecutionError:
            return False
