"""Application-specific exceptions with HTTP status codes."""


class AppError(Exception):
    """Base application error.

    Automatically mapped to a JSON envelope response by the global
    exception handler in ``app.main``.
    """

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, 404)


class AuthError(AppError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, 409)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, 422)


class LencoError(AppError):
    def __init__(self, message: str = "Payment provider error", status_code: int = 502):
        super().__init__(message, status_code)
