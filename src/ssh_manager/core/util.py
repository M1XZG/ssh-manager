from __future__ import annotations

import re

_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


def sanitize_filename(base: str) -> str:
    """Return a safe filename stem derived from base.

    Rules:
    - Take only the first whitespace-delimited token.
    - Remove characters not in allowed set (alnum, dot, dash, underscore).
    - Collapse consecutive disallowed characters into a single dash.
    - Strip leading dots to avoid hidden files.
    - Fallback to 'host' if empty after cleaning.
    """
    token = base.strip().split()[0] if base.strip() else base.strip()
    if not token:
        return "host"
    cleaned_chars = []
    last_was_sep = False
    for ch in token:
        if ch in _ALLOWED:
            cleaned_chars.append(ch)
            last_was_sep = False
        else:
            if not last_was_sep:
                cleaned_chars.append('-')
                last_was_sep = True
    cleaned = ''.join(cleaned_chars)
    # Remove leading dots produced by patterns like *.corp -> .corp
    cleaned = cleaned.lstrip('.')
    # Remove leading separators
    cleaned = cleaned.lstrip('-_')
    cleaned = re.sub(r'[-_]{2,}', '-', cleaned)  # collapse repeats
    if not cleaned:
        cleaned = 'host'
    return cleaned

__all__ = ["sanitize_filename"]
