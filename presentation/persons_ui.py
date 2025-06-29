# src/presentation/persons_ui.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableView, QPushButton,
                             QHBoxLayout, QMessageBox, QDialog, QLineEdit, QComboBox,
                             QFormLayout, QDialogButtonBox, QAbstractItemView,
                             QTextEdit, QHeaderView) # QDoubleSpinBox اینجا لازم نیست
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex
from PyQt5.QtGui import QColor # برای نمایش غیرفعال‌ها (اگر اشخاص هم وضعیت فعال/غیرفعال داشتند)

from typing import List, Optional, Any, Dict

# Import necessary entities, enums, and managers
from src.business_logic.entities.person_entity import PersonEntity
from src.constants import PersonType # Enum for person types
from src.business_logic.person_manager import PersonManager
import logging

logger = logging.getLogger(__name__)

# --- Custom Table Model for Persons ---
class PersonTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[PersonEntity]] = None, parent=None):
        super().__init__(parent)
        self._data: List[PersonEntity] = data if data is not None else []
        self._headers = ["شناسه", "نام شخص", "نوع شخص", "اطلاعات تماس"]

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
        person = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(person.id)
            elif col == 1:
                return person.name
            elif col == 2:
                return person.person_type.value # Display enum value
            elif col == 3:
                return person.contact_info if person.contact_info is not None else ""
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0: # ID
                 return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            # برای سایر ستون‌ها (نام، نوع، اطلاعات تماس) می‌توان AlignRight یا AlignLeft تنظیم کرد
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter 

        # اگر اشخاص هم فیلد is_active داشتند، می‌توانستیم مانند محصولات رنگشان را تغییر دهیم
        # elif role == Qt.ItemDataRole.ForegroundRole:
        #     if hasattr(person, 'is_active') and not person.is_active:
        #         return QColor(Qt.GlobalColor.gray)

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[PersonEntity]):
        logger.debug(f"Updating person table model with {len(new_data)} rows.")
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
        logger.debug("Person table model reset complete.")

    def get_person_at_row(self, row: int) -> Optional[PersonEntity]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

# --- Add/Edit Person Dialog ---
class PersonDialog(QDialog):
    def __init__(self, person_types: List[PersonType], person: Optional[PersonEntity] = None, parent=None):
        super().__init__(parent)
        self.person = person
        self.creatable_person_types = [pt for pt in person_types if pt != PersonType.EMPLOYEE]
        self.person_types_map = {pt.value: pt for pt in self.creatable_person_types}
        

        self.setWindowTitle("افزودن شخص جدید" if not person else f"ویرایش شخص: {person.name}")
        self.setMinimumWidth(350)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.name_edit = QLineEdit(self)
        self.type_combo = QComboBox(self)
        self.contact_info_edit = QTextEdit(self) # QTextEdit for potentially longer contact info
        self.contact_info_edit.setFixedHeight(80)


        self.type_combo.addItems([pt.value for pt in self.creatable_person_types])
        # اگر نوع شخص کارمند است، نباید از طریق این فرم تغییر کند (EmployeeManager مسئول است)
        # مگر اینکه بخواهیم اجازه دهیم یک مشتری/تامین‌کننده به کارمند تبدیل شود یا بالعکس (که پیچیده است)
        # فعلاً اجازه ویرایش نوع داده می‌شود، اما باید با احتیاط استفاده شود.


        if self.person: # Populate fields if editing
            self.name_edit.setText(self.person.name)
            self.type_combo.setCurrentText(self.person.person_type.value)
            self.contact_info_edit.setText(self.person.contact_info if self.person.contact_info else "")
            
            # If person_type is EMPLOYEE, maybe disable type_combo editing here?
            if self.person.person_type == PersonType.EMPLOYEE:
                self.type_combo.setEnabled(False) # تصمیم با شما
                self.type_combo.setToolTip("نوع 'کارمند' از طریق ماژول کارمندان مدیریت می‌شود.")
                pass


        layout.addRow("نام شخص:", self.name_edit)
        layout.addRow("نوع شخص:", self.type_combo)
        layout.addRow("اطلاعات تماس:", self.contact_info_edit)
        
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
            QMessageBox.warning(self, "ورودی نامعتبر", "نام شخص نمی‌تواند خالی باشد.")
            return None
        
        selected_type_value = self.type_combo.currentText()
        person_type_enum = self.person_types_map.get(selected_type_value)
        if not person_type_enum:
            QMessageBox.critical(self, "خطا", "نوع شخص انتخاب شده نامعتبر است.")
            return None

        # اگر در حال ویرایش هستیم و نوع شخص کارمند است و تغییر نکرده، اجازه می‌دهیم
        # اما اگر می‌خواهیم از نوع دیگری به کارمند تغییر دهیم یا کارمند را به نوع دیگری، باید هشدار دهیم یا جلوگیری کنیم
        if self.person and self.person.id is not None: # در حالت ویرایش
            if self.person.person_type == PersonType.EMPLOYEE and person_type_enum != PersonType.EMPLOYEE:
                 reply = QMessageBox.question(self, "تایید تغییر نوع",
                                             "این شخص یک کارمند است. تغییر نوع آن ممکن است اطلاعات کارمندی مرتبط را تحت تاثیر قرار دهد. آیا مطمئن هستید؟",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) # type: ignore
                 if reply == QMessageBox.StandardButton.No:
                     return None
            elif self.person.person_type != PersonType.EMPLOYEE and person_type_enum == PersonType.EMPLOYEE:
                 QMessageBox.warning(self, "تغییر نوع نامعتبر", "برای تبدیل یک شخص به کارمند، لطفاً از طریق ماژول مدیریت کارمندان اقدام کنید.")
                 return None
        if not person_type_enum: # اگر به هر دلیلی نوع نامعتبر انتخاب شد (نباید اتفاق بیفتد)
            # یا اگر نوع کارمند به نحوی انتخاب شد و ما آن را مجاز نمی‌دانیم از این فرم ایجاد شود
            QMessageBox.critical(self, "خطا", "نوع شخص انتخاب شده از این فرم قابل ایجاد/ویرایش نیست.")
            return None
        if self.person and self.person.person_type == PersonType.EMPLOYEE and person_type_enum != PersonType.EMPLOYEE:
            QMessageBox.warning(self, "تغییر نوع نامعتبر", "نوع یک کارمند موجود را نمی‌توان از این فرم تغییر داد.")
            return None # جلوگیری از تغییر نوع کارمند


        data = {
            "name": self.name_edit.text().strip(),
            "person_type": person_type_enum,
            "contact_info": self.contact_info_edit.toPlainText().strip()
        }
        return data

# --- Main Persons UI Widget ---
class PersonsUI(QWidget):
    def __init__(self, person_manager: PersonManager, parent=None):
        super().__init__(parent)
        self.person_manager = person_manager
        self.table_model = PersonTableModel()
        self._init_ui()
        self.load_persons_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSortingEnabled(True)

        header = self.table_view.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Name column
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Contact Info column
        
        self.table_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        main_layout.addWidget(self.table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("افزودن شخص جدید")
        self.edit_button = QPushButton("ویرایش شخص")
        self.delete_button = QPushButton("حذف شخص")
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_person_dialog)
        self.edit_button.clicked.connect(self._open_edit_person_dialog)
        self.delete_button.clicked.connect(self._delete_selected_person)
        self.refresh_button.clicked.connect(self.load_persons_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("PersonsUI initialized.")

    def load_persons_data(self):
        logger.debug("Loading persons data...")
        try:
            persons = self.person_manager.get_all_persons()
            self.table_model.update_data(persons)
            logger.info(f"{len(persons)} persons loaded into table.")
        except Exception as e:
            logger.error(f"Error loading persons: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا در بارگذاری", f"خطا در بارگذاری لیست اشخاص: {e}")

    def _open_add_person_dialog(self):
        logger.debug("Opening Add Person dialog.")
        person_types_for_dialog = [pt for pt in PersonType if pt != PersonType.EMPLOYEE]
      
        dialog = PersonDialog(person_types_for_dialog, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    # اگر کاربر نوع "کارمند" را انتخاب کند، PersonManager فقط رکورد Person را می‌سازد.
                    # جزئیات کارمندی باید از طریق EmployeeManager اضافه شود.
                    if data["person_type"] == PersonType.EMPLOYEE:
                        QMessageBox.information(self, "توجه",
                                                "برای افزودن کامل اطلاعات کارمند، لطفاً پس از ایجاد شخص پایه، "
                                                "از طریق ماژول 'مدیریت کارمندان' اقدام به تکمیل اطلاعات کنید.")

                    self.person_manager.add_person(
                        name=data["name"],
                        person_type=data["person_type"],
                        contact_info=data["contact_info"]
                    )
                    QMessageBox.information(self, "موفقیت", f"شخص '{data['name']}' با موفقیت اضافه شد.")
                    self.load_persons_data()
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error adding person: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در افزودن شخص: {e}")

    def _open_edit_person_dialog(self):
        selection_model = self.table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک شخص را برای ویرایش انتخاب کنید.")
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows: return

        selected_row_index = selected_rows[0].row()
        person_to_edit = self.table_model.get_person_at_row(selected_row_index)

        if not person_to_edit or person_to_edit.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات شخص برای ویرایش.")
            return

        logger.debug(f"Opening Edit Person dialog for Person ID: {person_to_edit.id}.")
        person_types_for_dialog = [pt for pt in PersonType if pt != PersonType.EMPLOYEE]
        dialog = PersonDialog(list(PersonType), person=person_to_edit, parent=self) # ارسال همه انواع، دیالوگ خودش فیلتر می‌کند
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    updated_person = self.person_manager.update_person(
                        person_id=person_to_edit.id, # type: ignore
                        name=data["name"],
                        person_type=data["person_type"],
                        contact_info=data["contact_info"]
                    )
                    if updated_person:
                        QMessageBox.information(self, "موفقیت", f"شخص '{updated_person.name}' با موفقیت ویرایش شد.")
                        self.load_persons_data()
                    else:
                         QMessageBox.warning(self, "هشدار", f"تغییری در اطلاعات شخص '{data['name']}' اعمال نشد یا شخص یافت نشد.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error editing person: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش شخص: {e}")

    def _delete_selected_person(self):
        selection_model = self.table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک شخص را برای حذف انتخاب کنید.")
            return
            
        selected_rows = selection_model.selectedRows()
        if not selected_rows: return

        selected_row_index = selected_rows[0].row()
        person_to_delete = self.table_model.get_person_at_row(selected_row_index)

        if not person_to_delete or person_to_delete.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات شخص برای حذف.")
            return

        # بررسی مهم: اگر شخص از نوع کارمند است، حذف آن از اینجا ممکن است رکورد Employee مرتبط را orphan کند
        # یا اگر ON DELETE CASCADE در دیتابیس برای employees.person_id تنظیم شده باشد، رکورد employee هم حذف می‌شود.
        # PersonManager.delete_person فعلی این وابستگی را مستقیماً مدیریت نمی‌کند و به دیتابیس متکی است.
        warning_message = ""
        if person_to_delete.person_type == PersonType.EMPLOYEE:
            warning_message = "\nهشدار: این شخص یک کارمند است. حذف او ممکن است اطلاعات کارمندی مرتبط را نیز حذف کند (بسته به تنظیمات پایگاه داده)."

        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        reply = QMessageBox.question(self, "تایید حذف", 
                                     f"آیا از حذف شخص '{person_to_delete.name}' (شناسه: {person_to_delete.id}) مطمئن هستید؟"
                                     f"{warning_message}\nاین عملیات قابل بازگشت نیست.",
                                     buttons, # type: ignore
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.debug(f"Attempting to delete Person ID: {person_to_delete.id}")
            try:
                success = self.person_manager.delete_person(person_to_delete.id) # type: ignore
                if success:
                    QMessageBox.information(self, "موفقیت", f"شخص '{person_to_delete.name}' با موفقیت حذف شد.")
                    self.load_persons_data()
                else: # PersonManager.delete_person برمی‌گرداند bool
                    QMessageBox.warning(self, "ناموفق", f"شخص '{person_to_delete.name}' حذف نشد. ممکن است در جای دیگری استفاده شده باشد.")
            except ValueError as ve: # اگر PersonManager خطای اعتبارسنجی بدهد
                 QMessageBox.critical(self, "خطا در حذف", str(ve))
            except Exception as e: # برای خطاهای دیگر مانند خطاهای پایگاه داده که PersonManager ممکن است raise کند
                logger.error(f"Error deleting person: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در حذف شخص: {e}")