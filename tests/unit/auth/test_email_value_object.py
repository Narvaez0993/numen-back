import pytest

from src.modules.auth.domain.value_objects.email import Email, InvalidEmailError


def test_email_normalizes_and_trims() -> None:
    email = Email.create("  Sebastian@Numen.APP  ")
    assert email.value == "sebastian@numen.app"


def test_email_rejects_malformed() -> None:
    with pytest.raises(InvalidEmailError):
        Email.create("not-an-email")
