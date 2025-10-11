import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """
    Telefon raqamini tekshirish.
    Qo'llab-quvvatlanadigan formatlar:
    - +998901234567
    - 998901234567
    - +7 918 123 45 67
    - 8 (918) 123-45-67
    """
    # Faqat raqamlarni qoldirish
    digits = re.sub(r'\D', '', phone)
    
    # Uzunlik: 10-15 raqam
    if len(digits) < 10 or len(digits) > 15:
        return False
    
    # Uzbekiston uchun: 998 bilan boshlanishi kerak
    # Yoki Rossiya uchun: 7/8 bilan
    if digits.startswith('998'):
        return len(digits) == 12  # 998XXXXXXXXX
    elif digits.startswith('7') or digits.startswith('8'):
        return len(digits) == 11  # 7XXXXXXXXXX yoki 8XXXXXXXXXX
    
    # Boshqa mamlakatlar uchun umumiy tekshirish
    return True


def format_phone(phone: str) -> str:
    """
    Telefon raqamini formatlash.
    +998901234567 -> +998 90 123 45 67
    """
    digits = re.sub(r'\D', '', phone)
    
    if digits.startswith('998') and len(digits) == 12:
        return f"+998 {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}"
    elif (digits.startswith('7') or digits.startswith('8')) and len(digits) == 11:
        return f"+{digits[0]} {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:]}"
    
    return phone


def calculate_profit(work_amount: float, expenses: float) -> float:
    """Foyda hisoblash"""
    return work_amount - expenses


def format_money(amount: float, currency: str = "₽") -> str:
    """Pul summasi formatlash (butun son sifatida)"""
    return f"{amount:,} {currency}".replace(",", " ")


def parse_datetime_str(dt_str: str) -> Optional[str]:
    """
    Turli formatdagi sana/vaqt stringlarini to'g'ri formatga o'tkazish.
    Returns: ISO format string yoki None
    """
    from datetime import datetime
    
    formats = [
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Matnni qisqartirish"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def get_status_emoji(status: str) -> str:
    """Status uchun emoji"""
    emoji_map = {
        "new": "🆕",
        "confirmed": "✅",
        "in_progress": "⚙️",
        "arrived": "🏠",
        "completed": "✔️",
        "rejected": "❌"
    }
    return emoji_map.get(status, "❓")