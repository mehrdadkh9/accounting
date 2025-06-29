# src/presentation/custom_widgets.py

from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout, QCalendarWidget, QDialog, QVBoxLayout, QGridLayout, QLabel
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QLocale
from datetime import date
from typing import Optional
import jdatetime
import logging

logger = logging.getLogger(__name__)

class ShamsiCalendarDialog(QDialog):
    """یک دیالوگ که یک تقویم شمسی برای انتخاب تاریخ نمایش می‌دهد."""
    dateSelected = pyqtSignal(date)

    def __init__(self, initial_date: Optional[date] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("انتخاب تاریخ")
        self.setModal(True)
        self.setLayout(QVBoxLayout())
        self.setMinimumSize(350, 300)

        if initial_date:
            self._current_jdate = jdatetime.date.fromgregorian(date=initial_date)
        else:
            self._current_jdate = jdatetime.date.today()
        
        self._setup_ui()
        self._generate_calendar()

    def _setup_ui(self):
        nav_layout = QHBoxLayout()
        self.prev_month_btn = QPushButton("<")
        self.next_month_btn = QPushButton(">")
        self.month_year_label = QLabel()
        self.month_year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_year_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.month_year_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_month_btn)
        self.layout().addLayout(nav_layout)

        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(5)
        
        days = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        for i, day in enumerate(days):
            label = QLabel(day)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: bold;")
            self.calendar_grid.addWidget(label, 0, i)
        
        self.layout().addLayout(self.calendar_grid)

        self.prev_month_btn.clicked.connect(self._go_to_prev_month)
        self.next_month_btn.clicked.connect(self._go_to_next_month)

    def _generate_calendar(self):
        # پاک کردن دکمه‌های روزهای ماه قبلی
        for i in reversed(range(self.calendar_grid.count())):
            item = self.calendar_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget and not isinstance(widget, QLabel): # فقط دکمه‌ها را حذف کن، نه سرستون‌ها
                    widget.setParent(None)
                    widget.deleteLater()

        self.month_year_label.setText(self._current_jdate.strftime("%B %Y"))

        first_day_of_month = self._current_jdate.replace(day=1)
        start_day_weekday = (first_day_of_month.weekday() + 1) % 7 # شنبه = 0
        
        # --- شروع اصلاح منطق محاسبه روزهای ماه ---
        year = self._current_jdate.year
        month = self._current_jdate.month
        
        if month <= 6:
            days_in_month = 31
        elif month < 12:
            days_in_month = 30
        else: # اسفند
            if jdatetime.date.isleap(year):
                days_in_month = 30
            else:
                days_in_month = 29
        # --- پایان اصلاح ---
        
        row = 1
        col = start_day_weekday

        for day_num in range(1, days_in_month + 1):
            day_btn = QPushButton(str(day_num))
            day_btn.setFixedSize(40, 40)
            day_btn.clicked.connect(self._day_clicked)
            
            today = jdatetime.date.today()
            if self._current_jdate.year == today.year and self._current_jdate.month == today.month and day_num == today.day:
                day_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 20px;")
            
            self.calendar_grid.addWidget(day_btn, row, col)
            
            col = (col + 1) % 7
            if col == 0:
                row += 1
    
    def _go_to_prev_month(self):
        year, month = self._current_jdate.year, self._current_jdate.month
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        self._current_jdate = self._current_jdate.replace(year=year, month=month, day=1)
        self._generate_calendar()

    def _go_to_next_month(self):
        year, month = self._current_jdate.year, self._current_jdate.month
        month += 1
        if month > 12:
            month = 1
            year += 1
        self._current_jdate = self._current_jdate.replace(year=year, month=month, day=1)
        self._generate_calendar()

    def _day_clicked(self):
        day_btn = self.sender()
        day = int(day_btn.text())
        
        selected_jdate = self._current_jdate.replace(day=day)
        gregorian_date = selected_jdate.togregorian()
        
        self.dateSelected.emit(gregorian_date)
        self.accept()

class ShamsiDateEdit(QWidget):
    """یک ویجت اختصاصی برای نمایش و انتخاب تاریخ شمسی."""
    dateChanged = pyqtSignal(date)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gregorian_date: Optional[date] = None
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.line_edit = QLineEdit(self)
        self.line_edit.setReadOnly(True)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.calendar_button = QPushButton("📅", self)
        self.calendar_button.setFixedWidth(40)
        
        self.main_layout.addWidget(self.line_edit)
        self.main_layout.addWidget(self.calendar_button)

        self.calendar_button.clicked.connect(self.open_calendar)
        
        self.setDate(date.today())

    def open_calendar(self):
        """دیالوگ تقویم شمسی را باز می‌کند."""
        dialog = ShamsiCalendarDialog(initial_date=self._gregorian_date, parent=self)
        dialog.dateSelected.connect(self.setDate)
        dialog.exec_()

    def setDate(self, gregorian_date: Optional[date]):
        """تاریخ ویجت را از یک آبجکت date استاندارد پایتون تنظیم می‌کند."""
        if gregorian_date is None:
            self._gregorian_date = None
            self.line_edit.setText("")
            return
            
        if not isinstance(gregorian_date, date):
            return

        self._gregorian_date = gregorian_date
        try:
            shamsi_date = jdatetime.date.fromgregorian(date=gregorian_date)
            self.line_edit.setText(shamsi_date.strftime("%Y/%m/%d"))
            self.dateChanged.emit(self._gregorian_date)
        except Exception as e:
            logger.error(f"Error converting date to Shamsi: {e}")
            self.line_edit.setText("تاریخ نامعتبر")

    def date(self) -> Optional[date]:
        """تاریخ فعلی را به صورت آبجکت date استاندارد پایتون برمی‌گرداند."""
        return self._gregorian_date

    def toPyDate(self) -> Optional[date]:
        """برای سازگاری با QDateEdit."""
        return self.date()