class NaukriClientError(Exception):
    """Base exception for all Naukri client errors."""
    pass


class NaukriAuthError(NaukriClientError):
    """Authentication / session related errors."""

    def __init__(self, message="Authentication failed", status_code=None):
        msg = f"[AUTH ERROR] {message}"
        if status_code:
            msg += f" | HTTP {status_code}"
        super().__init__(msg)


class NaukriNetworkError(NaukriClientError):
    """Network / request failures (timeouts, connection issues)."""

    def __init__(self, message="Network request failed", url=None):
        msg = f"[NETWORK ERROR] {message}"
        if url:
            msg += f" | URL: {url}"
        super().__init__(msg)


class NaukriParseError(NaukriClientError):
    """Invalid or unexpected API response."""

    def __init__(self, message="Failed to parse response", response_snippet=None):
        msg = f"[PARSE ERROR] {message}"
        if response_snippet:
            msg += f" | Response: {response_snippet[:200]}"
        super().__init__(msg)


class NaukriUploadError(NaukriClientError):
    """Resume / file upload failures."""

    def __init__(self, message="Upload failed", filename=None):
        msg = f"[UPLOAD ERROR] {message}"
        if filename:
            msg += f" | File: {filename}"
        super().__init__(msg)