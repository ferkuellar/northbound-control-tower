from __future__ import annotations

from oci.exceptions import ConfigFileNotFound, InvalidConfig, ServiceError


class OCIConfigurationError(ValueError):
    pass


def is_access_denied(error: Exception) -> bool:
    return isinstance(error, ServiceError) and error.status in {401, 403}


def oci_error_message(error: Exception) -> str:
    if isinstance(error, ServiceError):
        return f"{error.status} {error.code}: {error.message}"
    if isinstance(error, (ConfigFileNotFound, InvalidConfig, OCIConfigurationError)):
        return str(error)
    return str(error)
