"""
Text normalization, tokenization, and light stemming for LapLink smart search.
Pure functions with no external or Django dependencies.
"""
import re
from typing import List

# Arabic diacritics regex: fathatan, dammatan, kasratan, fatha, damma, kasra, shadda, sukun, dagger alif
ARABIC_DIACRITICS_RE = re.compile(r'[\u064B-\u0652\u0670]')
TATWEEL_CHAR = '\u0640'

# Arabic letter normalizations
ARABIC_ALIFS_RE = re.compile(r'[إأآٱ]')

# Arabic-Indic digits conversion table
ARABIC_INDIC_DIGITS = str.maketrans(
    '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
    '01234567890123456789'
)

# Allowed characters: alphanumeric, dash, dot, whitespace
CLEAN_CHARS_RE = re.compile(r'[^\w\s\-\.]|_')
WHITESPACE_RE = re.compile(r'\s+')
DECIMAL_RE = re.compile(r'^\d+\.\d+$')
SPLIT_PARTS_RE = re.compile(r'[\-\.]')


def normalize(text: str) -> str:
    """
    Normalizes text (English and Arabic):
    1. Lowercase (casefold)
    2. Remove Arabic diacritics and tatweel
    3. Unify Arabic letter variants (alifs, taa marbuta, alif maqsura, hamzas)
    4. Convert Arabic-Indic digits to standard 0-9
    5. Clean non-alphanumeric chars (preserving '-' and '.'), collapse whitespace
    """
    if not text:
        return ""
    
    text = text.casefold()
    
    # Remove diacritics and tatweel
    text = ARABIC_DIACRITICS_RE.sub('', text)
    text = text.replace(TATWEEL_CHAR, '')
    
    # Unify Arabic letters
    text = ARABIC_ALIFS_RE.sub('ا', text)
    text = text.replace('ة', 'ه')
    text = text.replace('ى', 'ي')
    text = text.replace('ؤ', 'و')
    text = text.replace('ئ', 'ي')
    
    # Convert digits
    text = text.translate(ARABIC_INDIC_DIGITS)
    
    # Replace chars not in [a-zA-Z0-9-.\s] with space
    text = CLEAN_CHARS_RE.sub(' ', text)
    
    # Replace repeated or non-word-internal dots/dashes (e.g. "...", "--", " - ") with space
    text = re.sub(r'[\.-]{2,}', ' ', text)
    text = re.sub(r'(?:(?<!\w)[\.-]|[\.-](?!\w))', ' ', text)
    
    # Collapse whitespace
    text = WHITESPACE_RE.sub(' ', text).strip()
    return text


def stem(token: str) -> str:
    """
    Light rule-based stemming applied at match time (not stored):
    - ASCII rules:
      - 'ies' -> 'y' (len > 4)
      - ends with ches|shes|sses|xes|zes -> strip 'es'
      - ends with 's' (len > 3 and not ending with 'ss') -> strip 's'
    - Arabic rules:
      - ends with 'ات' and len >= 5 -> strip 'ات'
      - ends with 'ه' and len >= 4 -> strip 'ه'
    """
    if not token:
        return ""
    
    if token.isascii():
        # English / ASCII rules
        if token.endswith('ies') and len(token) > 4:
            return token[:-3] + 'y'
        for suffix in ('ches', 'shes', 'sses', 'xes', 'zes'):
            if token.endswith(suffix):
                return token[:-2]
        if token.endswith('s') and len(token) > 3 and not token.endswith('ss'):
            return token[:-1]
        return token
    else:
        # Arabic rules
        if token.endswith('ات') and len(token) >= 5:
            return token[:-2]
        if token.endswith('ه') and len(token) >= 4:
            return token[:-1]
        return token


def tokenize(text: str) -> List[str]:
    """
    Tokenizes normalized text into distinct tokens, preserving insertion order.
    Handles hyphenated/dotted words and Arabic prefixes (ال, وال).
    """
    norm = normalize(text)
    if not norm:
        return []
    
    raw_tokens = norm.split(' ')
    result: List[str] = []
    seen = set()

    def add_token(t: str):
        t = t.strip('.-')
        if t and t not in seen:
            seen.add(t)
            result.append(t)

    for raw in raw_tokens:
        clean = raw.strip('.-')
        if not clean:
            continue
        
        # Arabic prefix stripping
        if clean.startswith('وال') and len(clean) >= 6:
            add_token(clean)
            add_token(clean[1:])   # Strip و -> الشاحن
            add_token(clean[3:])   # Strip وال -> شاحن
            continue
        elif clean.startswith('ال') and len(clean) >= 5:
            add_token(clean)
            add_token(clean[2:])   # Strip ال -> شاحن
            continue

        # Check for numbers like 15.6
        if DECIMAL_RE.match(clean):
            add_token(clean)
            continue
        
        # Check if token contains '-' or '.'
        if '-' in clean or '.' in clean:
            add_token(clean)
            joined = clean.replace('-', '').replace('.', '')
            if joined:
                add_token(joined)
            parts = SPLIT_PARTS_RE.split(clean)
            for part in parts:
                if len(part) >= 2:
                    add_token(part)
        else:
            add_token(clean)

    return result
