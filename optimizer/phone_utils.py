import re
import logging

logger = logging.getLogger(__name__)

def to_international(phone: str) -> str:
    """
    Convert any Algerian phone number to E.164 international format.

    Handles all common input formats:
      0555-123-456    ->  +213555123456
      0770 654 321    ->  +213770654321
      0555123456      ->  +213555123456
      +213555123456   ->  +213555123456  (already correct, returned as-is)
      213555123456    ->  +213555123456

    Algerian mobile prefixes after 213: 5xx, 6xx, 7xx (Ooredoo, Djezzy, Mobilis)

    Returns the original string unchanged if unrecognized.
    Prints a warning — caller should log this for admin review.
    """
    digits = re.sub(r'\D', '', phone)  # strip all non-digits

    if digits.startswith('213') and len(digits) == 12:
        return '+' + digits
    if digits.startswith('0') and len(digits) == 10:
        return '+213' + digits[1:]
    if len(digits) == 9 and digits[0] in ('5', '6', '7'):
        return '+213' + digits  # already without leading 0 or country code

    logger.warning(f"Phone '{phone}' is not a recognized Algerian mobile format. Using as-is.")
    return phone

def is_valid_algerian_mobile(phone: str) -> bool:
    """Validate after formatting. True if matches +213[567]XXXXXXXX"""
    return bool(re.match(r'^\+213[5-7]\d{8}$', phone))
