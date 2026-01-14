"""
Phone Number Validator and Normalizer
Handles E.164 formatting, validation, and cleaning
"""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Common country codes for validation
COUNTRY_CODES = {
    '1': 'US/CA',      # USA/Canada
    '44': 'UK',        # United Kingdom
    '91': 'IN',        # India
    '61': 'AU',        # Australia
    '49': 'DE',        # Germany
    '33': 'FR',        # France
    '86': 'CN',        # China
    '81': 'JP',        # Japan
    '52': 'MX',        # Mexico
    '55': 'BR',        # Brazil
}


def clean_phone_number(phone: str) -> str:
    """Remove all non-digit characters except leading +"""
    if not phone:
        return ""
    
    phone = str(phone).strip()
    
    # Preserve leading + if present
    has_plus = phone.startswith('+')
    
    # Remove all non-digit characters
    cleaned = re.sub(r'[^\d]', '', phone)
    
    # Re-add + if it was there
    if has_plus:
        cleaned = '+' + cleaned
    
    return cleaned


def normalize_to_e164(phone: str, default_country_code: str = '1') -> Tuple[str, bool, str]:
    """
    Normalize phone number to E.164 format
    
    Args:
        phone: Raw phone number string
        default_country_code: Default country code if none present (default: '1' for US)
    
    Returns:
        Tuple of (normalized_number, is_valid, error_message)
    """
    if not phone:
        return "", False, "Empty phone number"
    
    cleaned = clean_phone_number(phone)
    
    if not cleaned:
        return "", False, "No digits found in phone number"
    
    # Remove leading + for processing
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Check length
    if len(cleaned) < 7:
        return "", False, f"Phone number too short: {len(cleaned)} digits"
    
    if len(cleaned) > 15:
        return "", False, f"Phone number too long: {len(cleaned)} digits"
    
    # If starts with 0, likely local format - remove leading 0 and add country code
    if cleaned.startswith('0'):
        cleaned = default_country_code + cleaned[1:]
    
    # If 10 digits and no country code, assume default country
    if len(cleaned) == 10:
        cleaned = default_country_code + cleaned
    
    # Format as E.164
    normalized = '+' + cleaned
    
    # Validate structure (basic check)
    if not re.match(r'^\+\d{10,15}$', normalized):
        return "", False, f"Invalid phone format: {normalized}"
    
    return normalized, True, ""


def validate_phone_number(phone: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate a phone number and return status
    
    Returns:
        Tuple of (is_valid, status, normalized_number)
        status: "active" | "invalid" | "suspicious"
    """
    normalized, is_valid, error = normalize_to_e164(phone)
    
    if not is_valid:
        return False, "invalid", None
    
    # Check for suspicious patterns (all same digit, sequential, etc.)
    digits = normalized[1:]  # Remove +
    
    # All same digit
    if len(set(digits)) == 1:
        return False, "invalid", None
    
    # Sequential (123456...)
    if digits == ''.join(str(i % 10) for i in range(len(digits))):
        return False, "invalid", None
    
    # Test numbers
    if digits.startswith('555') or digits.startswith('1555'):
        return True, "suspicious", normalized
    
    return True, "active", normalized


def detect_duplicates(phone_list: list) -> dict:
    """
    Detect duplicate phone numbers in a list
    
    Args:
        phone_list: List of phone number strings
    
    Returns:
        Dict mapping normalized number to list of original indices
    """
    seen = {}
    duplicates = {}
    
    for idx, phone in enumerate(phone_list):
        normalized, is_valid, _ = normalize_to_e164(phone)
        
        if not is_valid or not normalized:
            continue
        
        if normalized in seen:
            if normalized not in duplicates:
                duplicates[normalized] = [seen[normalized]]
            duplicates[normalized].append(idx)
        else:
            seen[normalized] = idx
    
    return duplicates


def process_phone_list(phone_list: list, default_country_code: str = '1') -> list:
    """
    Process a list of phone numbers, normalizing and detecting issues
    
    Args:
        phone_list: List of raw phone numbers
        default_country_code: Default country code
    
    Returns:
        List of dicts with: original, normalized, status, error
    """
    results = []
    seen_normalized = set()
    
    for phone in phone_list:
        original = str(phone).strip() if phone else ""
        
        if not original:
            results.append({
                "original": original,
                "normalized": None,
                "status": "invalid",
                "error": "Empty phone number"
            })
            continue
        
        normalized, is_valid, error = normalize_to_e164(original, default_country_code)
        
        if not is_valid:
            results.append({
                "original": original,
                "normalized": None,
                "status": "invalid",
                "error": error
            })
            continue
        
        # Check for duplicates
        if normalized in seen_normalized:
            results.append({
                "original": original,
                "normalized": normalized,
                "status": "duplicate",
                "error": "Duplicate phone number"
            })
            continue
        
        seen_normalized.add(normalized)
        
        # Validate
        _, status, final_normalized = validate_phone_number(original)
        
        results.append({
            "original": original,
            "normalized": final_normalized or normalized,
            "status": status,
            "error": None
        })
    
    return results


def get_phone_stats(processed_list: list) -> dict:
    """Get statistics from a processed phone list"""
    stats = {
        "total": len(processed_list),
        "active": 0,
        "invalid": 0,
        "duplicate": 0,
        "suspicious": 0
    }
    
    for item in processed_list:
        status = item.get("status", "invalid")
        if status in stats:
            stats[status] += 1
    
    return stats
