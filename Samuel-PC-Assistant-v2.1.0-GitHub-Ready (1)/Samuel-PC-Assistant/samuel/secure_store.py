from __future__ import annotations

import platform
import subprocess


SERVICE = "SamuelPC Assistant"
ACCOUNT = "OPENAI_API_KEY"


def save_secret(secret: str) -> None:
    system = platform.system()
    if system == "Windows":
        _windows_save(secret)
    elif system == "Darwin":
        subprocess.run(
            ["security", "add-generic-password", "-U", "-s", SERVICE, "-a", ACCOUNT, "-w", secret],
            check=True,
            capture_output=True,
        )
    else:
        raise RuntimeError("Secure credential storage is supported on Windows and macOS.")


def load_secret() -> str | None:
    system = platform.system()
    if system == "Windows":
        return _windows_load()
    if system == "Darwin":
        result = subprocess.run(
            ["security", "find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    return None


def delete_secret() -> None:
    system = platform.system()
    if system == "Windows":
        import ctypes
        ctypes.windll.advapi32.CredDeleteW(SERVICE, 1, 0)
    elif system == "Darwin":
        subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", ACCOUNT], capture_output=True)


def _windows_save(secret: str) -> None:
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    blob = secret.encode("utf-16-le")
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    credential = CREDENTIAL(0, 1, SERVICE, None, wintypes.FILETIME(), len(blob), buffer, 2, 0, None, None, ACCOUNT)
    if not ctypes.windll.advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError()


def _windows_load() -> str | None:
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    pointer = ctypes.POINTER(CREDENTIAL)()
    if not ctypes.windll.advapi32.CredReadW(SERVICE, 1, 0, ctypes.byref(pointer)):
        return None
    try:
        credential = pointer.contents
        blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return blob.decode("utf-16-le")
    finally:
        ctypes.windll.advapi32.CredFree(pointer)
