from __future__ import annotations


class DomainError(Exception):
    """Base class for domain errors carrying a machine-readable error code.

    Messages must never include contract text (see DEVELOPMENT_SPEC.md #12).
    """

    error_code: str = "UNKNOWN_ERROR"
    user_message: str = "發生未預期的錯誤。"

    def __init__(self, error_code: str | None = None, user_message: str | None = None) -> None:
        self.error_code = error_code or self.error_code
        self.user_message = user_message or self.user_message
        super().__init__(self.error_code)


class UnsupportedFileTypeError(DomainError):
    error_code = "UNSUPPORTED_FILE_TYPE"
    user_message = "請上傳 .docx 格式的 Word 文件。"


class FileTooLargeError(DomainError):
    error_code = "FILE_TOO_LARGE"
    user_message = "檔案超過系統允許大小。"


class InvalidDocxError(DomainError):
    error_code = "INVALID_DOCX"
    user_message = "文件無法讀取，請確認檔案未毀損。"


class TrackedChangesNotSupportedError(DomainError):
    error_code = "TRACKED_CHANGES_NOT_SUPPORTED"
    user_message = "文件含修訂追蹤，請先接受或拒絕修訂後重新上傳。"


class DocumentNotReadyError(DomainError):
    error_code = "DOCUMENT_NOT_READY"
    user_message = "文件仍在解析，請稍後再試。"


class DocumentNotFoundError(DomainError):
    error_code = "DOCUMENT_NOT_FOUND"
    user_message = "找不到指定的文件。"


_ERROR_CODE_REGISTRY: dict[str, type[DomainError]] = {
    cls.error_code: cls
    for cls in (
        UnsupportedFileTypeError,
        FileTooLargeError,
        InvalidDocxError,
        TrackedChangesNotSupportedError,
        DocumentNotReadyError,
        DocumentNotFoundError,
    )
}


def error_for_code(error_code: str) -> DomainError:
    """Rebuild a DomainError with its documented user_message from a stored
    error_code (e.g. Document.error_code), instead of a generic message."""
    exception_class = _ERROR_CODE_REGISTRY.get(error_code, InvalidDocxError)
    return exception_class()
