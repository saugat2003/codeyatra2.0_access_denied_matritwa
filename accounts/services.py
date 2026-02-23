"""
accounts/services.py — Application-layer services for the Identity bounded context.

Encapsulates all user registration, authentication, and role-checking logic,
keeping views thin and business rules testable in isolation.
"""

import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Raised when volunteer registration fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class AuthenticationService:
    """Handles login / logout flows."""

    @staticmethod
    def login_user(request, username: str, password: str) -> bool:
        """
        Authenticate and log in the user.

        Returns True on success, False if credentials are invalid.
        """
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info("User '%s' logged in successfully.", username)
            return True
        logger.warning("Failed login attempt for username '%s'.", username)
        return False

    @staticmethod
    def logout_user(request) -> None:
        """Log out the current user."""
        username = request.user.username
        logout(request)
        logger.info("User '%s' logged out.", username)


class VolunteerRegistrationService:
    """
    Handles self-registration for healthcare volunteers (FCHV workers).

    All validation rules live here, not in the view.
    """

    # Minimum acceptable password length
    MIN_PASSWORD_LENGTH = 6

    def register(
        self,
        *,
        username: str,
        password1: str,
        password2: str,
        organization: str = "",
        education: str = "",
        age: str = "",
    ) -> User:
        """
        Validate inputs and create a new healthcare worker account.

        Returns the newly created (and saved) User.
        Raises RegistrationError with a list of validation messages on failure.
        """
        errors = self._validate(
            username=username,
            password1=password1,
            password2=password2,
            age=age,
        )
        if errors:
            raise RegistrationError(errors)

        user = User.objects.create_user(
            username=username,
            password=password1,
            organization=organization,
            education=education,
            age=int(age) if age else None,
            role=User.Role.HEALTHCARE_WORKER,
        )
        logger.info("New healthcare worker registered: '%s'.", username)
        return user

    def _validate(
        self,
        *,
        username: str,
        password1: str,
        password2: str,
        age: str,
    ) -> list[str]:
        errors: list[str] = []

        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append("That username is already taken.")

        if not password1:
            errors.append("Password is required.")
        elif password1 != password2:
            errors.append("Passwords do not match.")
        elif len(password1) < self.MIN_PASSWORD_LENGTH:
            errors.append(
                f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters."
            )

        if age and not age.isdigit():
            errors.append("Age must be a valid number.")

        return errors
