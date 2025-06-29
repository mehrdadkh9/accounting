# src/presentation/production_ui.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, 
    QMessageBox, QAbstractItemView, QHeaderView,QDialog ,QLabel,QLineEdit
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate, QSortFilterProxyModel
from typing import Optional, List
from .manual_production_models import ManualProductionTableModel 
from .manual_production_models import ManualProductionDialog # Assuming this is also imported

from src.constants import DATE_FORMAT, ProductType # Add any other constants you use from this file
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit # <<< ویجت جدید تاریخ شمسی
# --- Import های لازم ---
from src.business_logic.production_manager import ProductionManager
from src.business_logic.product_manager import ProductManager # برای پاس دادن به دیالوگ
# from .manual_production_models import ManualProductionTableModel # اگر در فایل جداگانه است
# from .manual_production_dialogs import ManualProductionDialog # اگر در فایل جداگانه است
from src.business_logic.entities.manual_production_entity import ManualProductionEntity # برای type hint
DATE_FORMAT = "%Y/%m/%d"
# <<< کد کلاس ManualProductionTableModel را اینجا کپی کنید اگر در فایل جداگانه نیست >>>
# <<< کد کلاس ConsumedMaterialDialog و ManualProductionDialog را اینجا کپی کنید اگر در فایل جداگانه نیستند >>>
# (بهتر است این کلاس‌ها در فایل‌های خودشان باشند و از اینجا import شوند)

import logging
logger = logging.getLogger(__name__)

class ManualProductionUI(QWidget):
    def __init__(self, 
                 production_manager: ProductionManager, 
                 product_manager: ProductManager, # برای پاس دادن به ManualProductionDialog
                 parent=None):
        super().__init__(parent)
        self.production_manager = production_manager
        self.product_manager = product_manager # برای استفاده در باز کردن دیالوگ‌ها

        self.table_model = ManualProductionTableModel()
         # --- مدل پروکسی برای فیلتر و جستجو ---
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterKeyColumn(-1)  # جستجو در تمام ستون‌ها
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._setup_ui()
        self.load_manual_productions_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
 # --- بخش جستجو و فیلتر ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("جستجو در محصول، تاریخ، توضیحات و ...")
        self.search_input.textChanged.connect(self.proxy_model.setFilterRegExp)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # --- جدول نمایش داده‌ها ---
        self.production_table_view = QTableView(self)
        self.production_table_view.setModel(self.proxy_model) # اتصال جدول به پروکسی مدل
        self.production_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.production_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.production_table_view.setSortingEnabled(True)
        self.production_table_view.setAlternatingRowColors(True)
        
       
        header = self.production_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # نام محصول نهایی
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # توضیحات
        
        self.production_table_view.sortByColumn(1, Qt.SortOrder.DescendingOrder) # مرتب‌سازی بر اساس تاریخ
        main_layout.addWidget(self.production_table_view)

        # --- دکمه‌ها ---
        button_layout = QHBoxLayout()
        self.add_button = QPushButton(" (+) ثبت تولید دستی جدید")
        self.edit_button = QPushButton("ویرایش رکورد انتخاب شده")
        self.delete_button = QPushButton("حذف رکورد انتخاب شده")
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_production_dialog)
        self.edit_button.clicked.connect(self._open_edit_production_dialog)
        self.delete_button.clicked.connect(self._delete_selected_production)
        self.refresh_button.clicked.connect(self.load_manual_productions_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("ManualProductionUI initialized.")

    def load_manual_productions_data(self):
        logger.debug("ManualProductionUI: Loading manual productions data...")
        try:
            productions = self.production_manager.get_all_manual_productions_summary()
            self.table_model.update_data(productions)
            logger.info(f"ManualProductionUI: {len(productions)} manual productions loaded.")
        except Exception as e:
            logger.error(f"Error loading manual productions: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لیست تولیدات: {e}")


    def _get_selected_production_header(self) -> Optional[ManualProductionEntity]:
        selection_model = self.production_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            return None
        selected_rows = selection_model.selectedRows()
        if not selected_rows: return None
        return self.table_model.get_production_header_at_row(selected_rows[0].row())

    def _open_add_production_dialog(self):
        logger.debug("ManualProductionUI: Opening Add Manual Production dialog.")
        # در اینجا production_manager به ManualProductionDialog پاس داده نمی‌شود
        # چون فقط برای واکشی جزئیات در حالت ویرایش لازم است.
        # اما product_manager برای پر کردن کمبوباکس‌ها در هر دو حالت لازم است.
        dialog = ManualProductionDialog(
            product_manager=self.product_manager, 
            parent=self
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_manual_production_data()
            if data:
                try:
                    created_production = self.production_manager.record_manual_production(
                        production_date=data["production_date"],
                        finished_product_id=data["finished_product_id"],
                        quantity_produced=data["quantity_produced"],
                        consumed_items_data=data["consumed_items_data"],
                        description=data.get("description")
                        # fiscal_year_id=data.get("fiscal_year_id") # اگر دارید
                    )
                    if created_production:
                        QMessageBox.information(self, "موفقیت", f"تولید دستی برای محصول '{getattr(created_production, 'finished_product_name', '')}' با موفقیت ثبت شد.")
                        self.load_manual_productions_data()
                    else:
                        QMessageBox.warning(self, "خطا", "ثبت تولید دستی ناموفق بود.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای ورودی", str(ve))
                except Exception as e:
                    logger.error(f"Error recording manual production: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطای سیستمی", f"خطا در ثبت تولید دستی: {e}")

    def _open_edit_production_dialog(self):
        selected_header = self._get_selected_production_header()
        if not selected_header or not selected_header.id:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک رکورد تولید را برای ویرایش انتخاب کنید.")
            return

        logger.debug(f"ManualProductionUI: Fetching details for MP ID {selected_header.id} for editing.")
        # برای ویرایش، باید رکورد کامل با اقلام مصرفی واکشی شود
        production_to_edit = self.production_manager.get_manual_production_with_details(selected_header.id)
        if not production_to_edit:
            QMessageBox.critical(self, "خطا", f"اطلاعات کامل تولید دستی با شناسه {selected_header.id} یافت نشد.")
            return

        dialog = ManualProductionDialog(
            product_manager=self.product_manager,
            production_to_edit=production_to_edit, # پاس دادن آبجکت کامل برای ویرایش
            parent=self
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_manual_production_data()
            if data and production_to_edit.id : # اطمینان از وجود شناسه برای ویرایش
                try:
                    # اینجا باید متد update_manual_production را در ProductionManager فراخوانی کنید
                    # این متد باید تغییرات در هدر و اقلام را مدیریت کند
                    updated_production = self.production_manager.update_manual_production(
                        production_id=production_to_edit.id, 
                        update_data=data # data شامل تمام فیلدهای هدر و consumed_items_data است
                    )
                    if updated_production:
                        QMessageBox.information(self, "موفقیت", "تولید دستی با موفقیت ویرایش شد.")
                        self.load_manual_productions_data()
                    else:
                        QMessageBox.warning(self, "خطا", "ویرایش تولید دستی ناموفق بود یا تغییری اعمال نشد.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای ورودی", str(ve))
                except Exception as e:
                    logger.error(f"Error updating manual production: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطای سیستمی", f"خطا در ویرایش تولید دستی: {e}")

    def _delete_selected_production(self):
        selected_header = self._get_selected_production_header()
        if not selected_header or not selected_header.id:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک رکورد تولید را برای حذف انتخاب کنید.")
            return

        product_name_display = getattr(selected_header, 'finished_product_name', f"ID محصول: {selected_header.finished_product_id}")
        reply = QMessageBox.question(self, "تایید حذف",
                                     f"آیا از حذف رکورد تولید دستی برای محصول '{product_name_display}' (تاریخ: {selected_header.production_date.strftime(DATE_FORMAT) if selected_header.production_date else ''}) مطمئن هستید؟\n"
                                     "توجه: این عملیات معمولاً موجودی انبار را برنمی‌گرداند.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.production_manager.delete_manual_production(selected_header.id):
                    QMessageBox.information(self, "موفقیت", "تولید دستی با موفقیت حذف شد.")
                    self.load_manual_productions_data()
                else:
                    QMessageBox.warning(self, "خطا", "حذف تولید دستی ناموفق بود.")
            except Exception as e:
                logger.error(f"Error deleting manual production: {e}", exc_info=True)
                QMessageBox.critical(self, "خطای سیستمی", f"خطا در حذف تولید دستی: {e}")