# src/utils/date_converter.py

from datetime import date, datetime
from typing import Optional, Union
import jdatetime

# اطمینان حاصل کنید که کتابخانه jdatetime نصب شده است: pip install jdatetime

def to_shamsi_str(gregorian_date: Optional[date]) -> str:
    """یک آبجکت date میلادی را به رشته تاریخ شمسی با فرمت YYYY/MM/DD تبدیل می‌کند."""
    if gregorian_date is None:
        return "-"
    if not isinstance(gregorian_date, (date, datetime)):
        return str(gregorian_date)
    
    try:
        shamsi_date = jdatetime.date.fromgregorian(date=gregorian_date)
        return shamsi_date.strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return "تاریخ نامعتبر"

def to_gregorian_date(shamsi_date_str: str) -> Optional[date]:
    """یک رشته تاریخ شمسی با فرمت YYYY/MM/DD را به آبجکت date میلادی تبدیل می‌کند."""
    if not isinstance(shamsi_date_str, str) or not shamsi_date_str:
        return None
    
    try:
        parts = list(map(int, shamsi_date_str.split('/')))
        if len(parts) != 3: return None
        j_date = jdatetime.date(parts[0], parts[1], parts[2])
        return j_date.togregorian()
    except (ValueError, TypeError, IndexError):
        return None

def from_qdate(q_date: 'QDate') -> date:
    """یک آبجکت QDate از PyQt را به date استاندارد پایتون تبدیل می‌کند."""
    return q_date.toPyDate()

def to_qdate(g_date: Optional[Union[date, datetime]]) -> 'QDate':
    """یک آبجکت date استاندارد پایتون را به QDate از PyQt تبدیل می‌کند."""
    from PyQt5.QtCore import QDate
    if g_date is None:
        return QDate.currentDate()
    return QDate(g_date.year, g_date.month, g_date.day)