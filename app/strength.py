"""Password strength evaluation logic."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.common_passwords import COMMON_PASSWORDS

SEQUENCE_SOURCES = [
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
]


@dataclass(frozen=True)
class PasswordStats:
    length: int
    uppercase: int
    lowercase: int
    digits: int
    symbols: int


@dataclass(frozen=True)
class PasswordCheckResult:
    score: int
    level: str
    stats: PasswordStats
    flags: dict[str, bool]
    suggestions: list[str]


def _contains_sequence(value: str, min_len: int = 3) -> bool:
    normalized = value.lower()
    if len(normalized) < min_len:
        return False

    for source in SEQUENCE_SOURCES:
        reverse_source = source[::-1]
        for size in range(min_len, min(len(normalized), 6) + 1):
            for idx in range(0, len(normalized) - size + 1):
                part = normalized[idx : idx + size]
                if part in source or part in reverse_source:
                    return True
    return False


def _contains_repeated_chars(value: str) -> bool:
    return bool(re.search(r"(.)\1{2,}", value))


def _contains_repeated_pattern(value: str) -> bool:
    return bool(re.search(r"(.{2,4})\1+", value))


def _build_stats(password: str) -> PasswordStats:
    uppercase = sum(1 for ch in password if ch.isupper())
    lowercase = sum(1 for ch in password if ch.islower())
    digits = sum(1 for ch in password if ch.isdigit())
    symbols = sum(1 for ch in password if not ch.isalnum())

    return PasswordStats(
        length=len(password),
        uppercase=uppercase,
        lowercase=lowercase,
        digits=digits,
        symbols=symbols,
    )


def _build_level(score: int) -> str:
    if score < 40:
        return "弱"
    if score < 70:
        return "中"
    if score < 90:
        return "强"
    return "极强"


def evaluate_password(password: str) -> PasswordCheckResult:
    stats = _build_stats(password)
    lower = password.lower()

    is_common = lower in COMMON_PASSWORDS
    has_sequence = _contains_sequence(password)
    has_repeat_char = _contains_repeated_chars(password)
    has_repeat_pattern = _contains_repeated_pattern(password)

    types_count = sum(
        [
            stats.uppercase > 0,
            stats.lowercase > 0,
            stats.digits > 0,
            stats.symbols > 0,
        ]
    )

    score = 0

    # Length contribution: up to 40 points.
    score += min(stats.length, 20) * 2

    # Character diversity: up to 50 points.
    score += types_count * 10
    if types_count == 4:
        score += 10
    if stats.length >= 12 and types_count >= 3:
        score += 5

    # Penalties.
    if stats.length < 8:
        score -= 20
    if is_common:
        score -= 40
    if has_sequence:
        score -= 15
    if has_repeat_char:
        score -= 15
    if has_repeat_pattern:
        score -= 10

    score = max(0, min(100, score))

    suggestions: list[str] = []
    if stats.length < 12:
        suggestions.append("长度建议至少 12 位")
    if types_count < 3:
        suggestions.append("增加大写/小写/数字/符号中的更多类型")
    if is_common:
        suggestions.append("避免使用常见密码，尝试随机组合短语")
    if has_sequence:
        suggestions.append("避免连续字符或键盘顺序（如 123、qwe）")
    if has_repeat_char or has_repeat_pattern:
        suggestions.append("避免重复字符或重复片段")
    if not suggestions and score >= 90:
        suggestions.append("密码强度优秀，请妥善保管并定期更换")
    if not suggestions and score >= 70:
        suggestions.append("当前密码已较强，可继续保持随机组合并避免多站复用")

    return PasswordCheckResult(
        score=score,
        level=_build_level(score),
        stats=stats,
        flags={
            "is_common": is_common,
            "has_sequence": has_sequence,
            "has_repeat_char": has_repeat_char,
            "has_repeat_pattern": has_repeat_pattern,
        },
        suggestions=suggestions,
    )
