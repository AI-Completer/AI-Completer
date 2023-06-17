from typing import NoReturn

class BaseError(Exception):
    """Base Exception."""

class RemoteError(BaseError):
    """Remote Exception."""

    def __init__(self, remote_exception: Exception, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remote_exception = remote_exception

    def reraise(self) -> NoReturn:
        raise self.remote_exception from BaseError('Remote Error')

class ProtocalError(BaseError):
    """Protocal error."""
