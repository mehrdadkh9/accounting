# src/presentation/employees_ui.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableView, QPushButton,
                             QHBoxLayout, QMessageBox, QDialog, QLineEdit, QComboBox,
                             QFormLayout, QDialogButtonBox, QAbstractItemView,
                             QDoubleSpinBox, QTextEdit, QHeaderView, QCheckBox, QDateEdit) # QDateEdit اضافه شد
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate
from PyQt5.QtGui import QColor

from typing import List, Optional, Any, Dict
from datetime import date

# Import necessary entities, enums, and managers
from src.business_logic.entities.person_entity import PersonEntity # برای ارجاع به نوع در صورت نیاز
from src.business_logic.entities.employee_entity import EmployeeEntity # برای ارجاع به نوع در صورت نیاز
from src.constants import PersonType, DATE_FORMAT # DATE_FORMAT برای نمایش تاریخ
from src.business_logic.employee_manager import EmployeeManager
import logging

logger = logging.getLogger(__name__)

# --- Custom Table Model for Employees ---
class EmployeeTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        # data is a list of dictionaries, each from EmployeeManager.get_all_employee_details()
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["کد کارمندی", "نام کامل", "کد ملی", "سمت", "حقوق پایه", "تاریخ استخدام", "وضعیت"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()
        
        if not (0 <= row < len(self._data)):
            return QVariant()
        employee_details = self._data[row] # This is a dictionary

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: # کد کارمندی
                return str(employee_details.get("employee_id", ""))
            elif col == 1: # نام کامل
                return employee_details.get("name", "")
            elif col == 2: # کد ملی
                return employee_details.get("national_id", "")
            elif col == 3: # سمت
                return employee_details.get("position", "")
            elif col == 4: # حقوق پایه
                salary = employee_details.get("base_salary", 0.0)
                return f"{salary:,.2f}" if isinstance(salary, (int, float)) else ""
            elif col == 5: # تاریخ استخدام
                hire_date_str = employee_details.get("hire_date") # Expects string in DATE_FORMAT
                return hire_date_str if hire_date_str else ""
            elif col == 6: # وضعیت
                is_active = employee_details.get("is_active", False)
                return "فعال" if is_active else "غیرفعال"
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0: # ID
                 return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            if col == 1: # ID
                 return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if col == 4: # Salary
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ForegroundRole:
            if not employee_details.get("is_active", True): # Default to True if key missing
                return QColor(Qt.GlobalColor.gray)

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        logger.debug(f"Updating employee table model with {len(new_data)} rows.")
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
        logger.debug("Employee table model reset complete.")

    def get_employee_data_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

# --- Add/Edit Employee Dialog ---
class EmployeeDialog(QDialog):
    def __init__(self, initial_employee_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        # داده‌های اولیه کارمند (اگر در حالت ویرایش هستیم) را ذخیره می‌کنیم
        self.initial_employee_data = initial_employee_data 
        is_edit_mode = self.initial_employee_data is not None

        self.setWindowTitle("افزودن کارمند جدید" if not is_edit_mode else f"ویرایش کارمند: {self.initial_employee_data.get('name', '') if self.initial_employee_data else ''}") # type: ignore
        self.setMinimumWidth(400)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.name_edit = QLineEdit(self)
        self.contact_info_edit = QTextEdit(self) 
        self.contact_info_edit.setFixedHeight(60)
        self.national_id_edit = QLineEdit(self)
        self.position_edit = QLineEdit(self)
        self.base_salary_spinbox = QDoubleSpinBox(self)
        self.hire_date_edit = QDateEdit(self)
        self.hire_date_edit.setCalendarPopup(True)
        self.hire_date_edit.setDisplayFormat("yyyy-MM-dd") # فرمت استاندارد
        self.is_active_checkbox = QCheckBox("فعال", self)

        self.base_salary_spinbox.setDecimals(2)
        self.base_salary_spinbox.setMinimum(0.00)
        self.base_salary_spinbox.setMaximum(999999999.99)
        self.base_salary_spinbox.setGroupSeparatorShown(True)

        if is_edit_mode and self.initial_employee_data: # بررسی صریح که None نباشد
            # حالا Pylance باید بداند که initial_employee_data یک Dict است
            details: Dict[str, Any] = self.initial_employee_data 
            
            self.name_edit.setText(details.get("name", ""))
            self.contact_info_edit.setText(details.get("contact_info", ""))
            self.national_id_edit.setText(details.get("national_id", ""))
            self.position_edit.setText(details.get("position", ""))
            self.base_salary_spinbox.setValue(details.get("base_salary", 0.0)) # <<< استفاده از details
            
            hire_date_str = details.get("hire_date")
            if hire_date_str and isinstance(hire_date_str, str): # بررسی اضافی برای اطمینان از رشته بودن
                self.hire_date_edit.setDate(QDate.fromString(hire_date_str, "yyyy-MM-dd"))
            else: # اگر تاریخ استخدام وجود نداشت یا فرمت نامعتبر بود، تاریخ فعلی
                self.hire_date_edit.setDate(QDate.currentDate()) 
            
            self.is_active_checkbox.setChecked(details.get("is_active", True))
        else: # حالت افزودن
            self.hire_date_edit.setDate(QDate.currentDate())
            self.is_active_checkbox.setChecked(True)

        layout.addRow("نام کامل:", self.name_edit)
        layout.addRow("اطلاعات تماس:", self.contact_info_edit)
        layout.addRow("کد ملی:", self.national_id_edit)
        layout.addRow("سمت:", self.position_edit)
        layout.addRow("حقوق پایه:", self.base_salary_spinbox)
        layout.addRow("تاریخ استخدام:", self.hire_date_edit)
        layout.addRow("", self.is_active_checkbox)
        
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons, Qt.Orientation.Horizontal, self) # type: ignore
        
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
    def get_data(self) -> Optional[Dict[str, Any]]:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "ورودی نامعتبر", "نام کارمند نمی‌تواند خالی باشد.")
            return None
        
        hire_date_qdate = self.hire_date_edit.date()
        hire_date_py = date(hire_date_qdate.year(), hire_date_qdate.month(), hire_date_qdate.day())

        data_dict = {
            "name": self.name_edit.text().strip(),
            "contact_info": self.contact_info_edit.toPlainText().strip(),
            "national_id": self.national_id_edit.text().strip() or None,
            "position": self.position_edit.text().strip() or None,
            "base_salary": self.base_salary_spinbox.value(),
            "hire_date": hire_date_py,
            "is_active": self.is_active_checkbox.isChecked()
        }
        
        # اگر در حالت ویرایش هستیم و داده‌های اولیه موجودند، employee_id و person_id را هم برمی‌گردانیم
        if self.initial_employee_data and "employee_id" in self.initial_employee_data:
            data_dict["employee_id"] = self.initial_employee_data["employee_id"]
            if "person_id" in self.initial_employee_data:
                 data_dict["person_id"] = self.initial_employee_data["person_id"]

        return data_dict

# --- Main Employees UI Widget ---
class EmployeesUI(QWidget):
    def __init__(self, employee_manager: EmployeeManager, parent=None):
        super().__init__(parent)
        self.employee_manager = employee_manager
        self.table_model = EmployeeTableModel()
        self.show_active_employees_only = True # Default filter
        self._init_ui()
        self.load_employees_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # Filter checkbox
        self.active_filter_checkbox = QCheckBox("فقط نمایش کارمندان فعال", self)
        self.active_filter_checkbox.setChecked(self.show_active_employees_only)
        self.active_filter_checkbox.stateChanged.connect(self._on_filter_changed)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.active_filter_checkbox)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSortingEnabled(True)

        header = self.table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Name column
        
        self.table_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        main_layout.addWidget(self.table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("افزودن کارمند جدید")
        self.edit_button = QPushButton("ویرایش اطلاعات کارمند")
        self.toggle_activity_button = QPushButton("تغییر وضعیت (فعال/غیرفعال)")
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_employee_dialog)
        self.edit_button.clicked.connect(self._open_edit_employee_dialog)
        self.toggle_activity_button.clicked.connect(self._toggle_selected_employee_activity)
        self.refresh_button.clicked.connect(self.load_employees_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.toggle_activity_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("EmployeesUI initialized.")
        
    def _on_filter_changed(self, state: int):
        self.show_active_employees_only = self.active_filter_checkbox.isChecked()
        self.load_employees_data()

    def load_employees_data(self):
        logger.debug(f"Loading employees data... (Active only: {self.show_active_employees_only})")
        try:
            employees_details = self.employee_manager.get_all_employee_details(active_only=self.show_active_employees_only)
            self.table_model.update_data(employees_details)
            logger.info(f"{len(employees_details)} employees loaded into table.")
        except Exception as e:
            logger.error(f"Error loading employees: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا در بارگذاری", f"خطا در بارگذاری لیست کارمندان: {e}")

    def _open_add_employee_dialog(self):
        logger.debug("Opening Add Employee dialog.")
        dialog = EmployeeDialog(parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    # EmployeeManager.add_employee expects individual fields
                    person_entity, employee_entity = self.employee_manager.add_employee( # type: ignore
                        name=data["name"],
                        contact_info=data.get("contact_info"),
                        national_id=data.get("national_id"),
                        position=data.get("position"),
                        base_salary=data["base_salary"],
                        hire_date=data["hire_date"],
                        is_active=data["is_active"]
                    )
                    if employee_entity:
                        QMessageBox.information(self, "موفقیت", f"کارمند '{data['name']}' با موفقیت اضافه شد.")
                        self.load_employees_data()
                    else: # Should not happen if no exception from manager
                        QMessageBox.warning(self, "خطا", "خطا در افزودن کارمند. جزئیات در لاگ.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error adding employee: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در افزودن کارمند: {e}")

    def _open_edit_employee_dialog(self):
        selected_row_data = self.table_model.get_employee_data_at_row(self.table_view.currentIndex().row())
        if not selected_row_data:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک کارمند را برای ویرایش انتخاب کنید.")
            return

        employee_id = selected_row_data.get("employee_id")
        if employee_id is None:
             QMessageBox.critical(self, "خطا", "شناسه کارمند برای ویرایش یافت نشد.")
             return
        
        # current_employee_details همان selected_row_data است که از جدول خوانده شده
        # و شامل اطلاعات لازم برای پر کردن دیالوگ است.
        
        # <<< اصلاح در این خط: employee_details به initial_employee_data تغییر نام یافت >>>
        dialog = EmployeeDialog(initial_employee_data=selected_row_data, parent=self)
        
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    updated_employee_details = self.employee_manager.update_employee_details(
                        employee_id=employee_id, # از selected_row_data یا data اگر شاملش باشد
                        name=data["name"],
                        contact_info=data.get("contact_info"),
                        national_id=data.get("national_id"),
                        position=data.get("position"),
                        base_salary=data["base_salary"],
                        hire_date=data["hire_date"],
                        is_active=data["is_active"]
                    )
                    if updated_employee_details:
                        QMessageBox.information(self, "موفقیت", f"اطلاعات کارمند '{data['name']}' با موفقیت ویرایش شد.")
                        self.load_employees_data()
                    else:
                         QMessageBox.warning(self, "هشدار", "تغییری در اطلاعات کارمند اعمال نشد.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error editing employee: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش اطلاعات کارمند: {e}")

    def _toggle_selected_employee_activity(self):
        selected_row_data = self.table_model.get_employee_data_at_row(self.table_view.currentIndex().row())
        if not selected_row_data:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک کارمند را انتخاب کنید.")
            return

        employee_id = selected_row_data.get("employee_id")
        current_name = selected_row_data.get("name", "کارمند")
        current_is_active = selected_row_data.get("is_active", True)
        
        if employee_id is None:
             QMessageBox.critical(self, "خطا", "شناسه کارمند برای تغییر وضعیت یافت نشد.")
             return

        new_active_state = not current_is_active
        action_text = "فعال" if new_active_state else "غیرفعال"
        
        reply = QMessageBox.question(self, f"تایید تغییر وضعیت", 
                                     f"آیا از {action_text} کردن کارمند '{current_name}' (کد: {employee_id}) مطمئن هستید؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # type: ignore
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # EmployeeManager.set_employee_activity returns updated details dict or None
                updated_details = self.employee_manager.set_employee_activity(employee_id, new_active_state)
                if updated_details:
                    QMessageBox.information(self, "موفقیت", f"وضعیت کارمند '{current_name}' با موفقیت به '{action_text}' تغییر یافت.")
                    self.load_employees_data()
                else:
                    QMessageBox.warning(self, "ناموفق", f"تغییر وضعیت کارمند '{current_name}' انجام نشد.")
            except ValueError as ve:
                 QMessageBox.critical(self, "خطا", str(ve))
            except Exception as e:
                logger.error(f"Error toggling employee activity: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در تغییر وضعیت کارمند: {e}")