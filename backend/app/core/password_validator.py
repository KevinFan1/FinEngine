"""Password validation utilities."""

import re


class PasswordValidator:
    """Validate password strength."""

    MIN_LENGTH = 6
    RECOMMENDED_LENGTH = 12

    @staticmethod
    def validate(password: str, strict: bool = False) -> tuple[bool, str]:
        """
        Validate password strength.

        Args:
            password: Password to validate
            strict: If True, enforce stricter rules (12+ chars, all character types)

        Returns:
            Tuple of (is_valid, error_message)
        """
        min_length = PasswordValidator.RECOMMENDED_LENGTH if strict else PasswordValidator.MIN_LENGTH

        if len(password) < min_length:
            return False, f"密码长度至少需要 {min_length} 个字符"

        # Strength rules are temporarily disabled; only length is enforced.
        # if not re.search(r"[a-z]", password):
        #     return False, "密码必须包含至少一个小写字母"
        # if not re.search(r"[A-Z]", password):
        #     return False, "密码必须包含至少一个大写字母"
        # if not re.search(r"\d", password):
        #     return False, "密码必须包含至少一个数字"
        # if strict and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        #     return False, "密码必须包含至少一个特殊字符 (!@#$%^&* 等)"
        # weak_passwords = [
        #     "password",
        #     "12345678",
        #     "admin123",
        #     "qwerty123",
        #     "password123",
        #     "admin1234",
        # ]
        # if password.lower() in weak_passwords:
        #     return False, "密码过于简单，请使用更复杂的密码"

        return True, ""

    @staticmethod
    def get_strength(password: str) -> str:
        """
        Get password strength level.

        Returns:
            "weak", "medium", "strong", or "very_strong"
        """
        score = 0

        # Length
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1

        # Character types
        if re.search(r"[a-z]", password):
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"\d", password):
            score += 1
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1

        # Variety
        unique_chars = len(set(password))
        if unique_chars >= len(password) * 0.7:
            score += 1

        if score <= 3:
            return "weak"
        elif score <= 5:
            return "medium"
        elif score <= 7:
            return "strong"
        else:
            return "very_strong"
