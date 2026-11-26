"""HU-01 · account creation rules that the use-case tests hide behind fakes.

The register tests use a fake hasher, so they cannot tell whether the password is
really stored as a salted key-derivation hash. These use the real Argon2 adapter.
"""

from src.modules.auth.adapters.outbound.crypto.argon2_hasher import Argon2Hasher
from src.modules.auth.domain.value_objects.preferences import UserPreferences

PASSWORD = "correct horse battery"


def test_hu01_a_colombian_device_gets_spanish_and_cop() -> None:
    """HU-01 · «Registro con idioma y moneda tomados de la región» (Colombia)."""
    preferences = UserPreferences.default(language="es", currency="COP")

    assert preferences.language == "es"
    assert preferences.currency == "COP"


def test_hu01_the_region_currency_is_normalised() -> None:
    assert UserPreferences.default(language="es", currency=" cop ").currency == "COP"


def test_hu01_an_unsupported_currency_falls_back_instead_of_blocking_the_signup() -> None:
    """The region may report a currency the app cannot hold; sign-up still works."""
    default = UserPreferences.default()
    preferences = UserPreferences.default(language="es", currency="XXX")

    assert preferences.currency == default.currency
    assert preferences.language == "es"


def test_hu01_an_unsupported_language_falls_back_to_spanish() -> None:
    assert UserPreferences.default(language="fr", currency="COP").language == "es"


def test_hu01_the_password_is_stored_as_a_salted_argon2id_hash() -> None:
    """HU-01 · «La contraseña nunca se guarda en texto plano»."""
    hashed = Argon2Hasher().hash(PASSWORD)

    assert hashed.value.startswith("$argon2id$")
    assert PASSWORD not in hashed.value


def test_hu01_hashing_the_same_password_twice_gives_different_hashes() -> None:
    """A per-hash salt: equal passwords must not be recognisable in the database."""
    hasher = Argon2Hasher()

    assert hasher.hash(PASSWORD).value != hasher.hash(PASSWORD).value


def test_hu01_verify_accepts_the_right_password_and_rejects_the_wrong_one() -> None:
    hasher = Argon2Hasher()
    hashed = hasher.hash(PASSWORD)

    assert hasher.verify(hashed, PASSWORD) is True
    assert hasher.verify(hashed, "another password") is False
