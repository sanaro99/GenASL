#!/usr/bin/env python3
"""Export YouTube cookies from Edge to a Netscape cookies.txt file.

Usage:  python scripts/export_cookies.py

The script copies Edge's cookie database (to avoid the lock),
decrypts the cookies using Windows DPAPI, and writes them in
Netscape cookies.txt format that yt-dlp can consume.

Outputs:  cookies.txt  in the project root.

NOTE: Close Microsoft Edge before running for best results.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Windows-only DPAPI decryption
if os.name == "nt":
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    def _dpapi_decrypt(encrypted: bytes) -> bytes:
        blob_in = DATA_BLOB(len(encrypted), ctypes.create_string_buffer(encrypted, len(encrypted)))
        blob_out = DATA_BLOB()
        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return data
        return b""
else:
    def _dpapi_decrypt(encrypted: bytes) -> bytes:
        raise NotImplementedError("DPAPI only available on Windows")


def _get_edge_key() -> bytes | None:
    """Read and decrypt the AES key from Edge's Local State."""
    import json, base64
    local_state = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Edge" / "User Data" / "Local State"
    if not local_state.is_file():
        return None
    with open(local_state, "r", encoding="utf-8") as f:
        state = json.load(f)
    b64_key = state.get("os_crypt", {}).get("encrypted_key")
    if not b64_key:
        return None
    key_bytes = base64.b64decode(b64_key)
    if key_bytes[:5] == b"DPAPI":
        return _dpapi_decrypt(key_bytes[5:])
    return None


def _aes_decrypt(encrypted_value: bytes, key: bytes) -> str:
    """Decrypt a Chromium AES-GCM encrypted cookie value."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        print("ERROR: pip install cryptography  is required for cookie decryption.")
        sys.exit(1)

    # v10/v20 prefix (3 bytes) + 12-byte nonce + ciphertext
    if encrypted_value[:3] in (b"v10", b"v20"):
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:]
        try:
            return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
        except Exception:
            return ""
    # Older DPAPI-only encryption
    decrypted = _dpapi_decrypt(encrypted_value)
    return decrypted.decode("utf-8", errors="replace") if decrypted else ""


def main() -> None:
    if os.name != "nt":
        print("This script only works on Windows (Edge + DPAPI).")
        sys.exit(1)

    cookies_db = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Cookies"
    if not cookies_db.is_file():
        print(f"Edge cookies DB not found at {cookies_db}")
        sys.exit(1)

    key = _get_edge_key()
    if not key:
        print("Could not extract Edge encryption key from Local State.")
        sys.exit(1)

    # Copy the DB to a temp file to avoid lock issues
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    shutil.copy2(cookies_db, tmp_path)

    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.execute(
            "SELECT host_key, path, is_secure, expires_utc, name, encrypted_value "
            "FROM cookies WHERE host_key LIKE '%youtube%' OR host_key LIKE '%google%'"
        )
        rows = cursor.fetchall()
        conn.close()
    finally:
        os.unlink(tmp_path)

    if not rows:
        print("No YouTube/Google cookies found in Edge.")
        sys.exit(1)

    out_path = Path(__file__).resolve().parent.parent / "cookies.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for host, path, secure, expires, name, enc_val in rows:
            value = _aes_decrypt(enc_val, key) if enc_val else ""
            if not value:
                continue
            domain_flag = "TRUE" if host.startswith(".") else "FALSE"
            secure_flag = "TRUE" if secure else "FALSE"
            # Chrome epoch: microseconds since 1601-01-01  →  Unix seconds
            exp_unix = max(0, (expires - 11644473600000000) // 1000000) if expires else 0
            f.write(f"{host}\t{domain_flag}\t{path}\t{secure_flag}\t{exp_unix}\t{name}\t{value}\n")

    print(f"Exported {len(rows)} cookies → {out_path}")
    print("Now re-run the pipeline — yt-dlp will use cookies.txt automatically.")


if __name__ == "__main__":
    main()
