# Custom exceptions for domain layer
class ScraperException(Exception):
    """Base exception for all scraper-related errors."""

    pass


class AuthenticationError(ScraperException):
    """Exception raised for failed login attempts."""

    pass


class WebDriverError(ScraperException):
    """Exception raised for errors related to the web driver."""

    pass


class DataExtractionError(ScraperException):
    """Exception raised when data cannot be extracted from the page."""

    pass
