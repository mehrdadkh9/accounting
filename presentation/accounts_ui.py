# src/presentation/accounts_ui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout,
    QDialogButtonBox, QAbstractItemView, QDoubleSpinBox, QTextEdit,
    QHeaderView, QCheckBox
)
from PyQt5.QtCore import Qt, QAbstractItemModel, QVariant, QModelIndex
from PyQt5.QtGui import QColor

from typing import List, Optional, Any, Dict

# Import necessary entities, enums, and managers
from src.business_logic.entities.account_entity import AccountEntity
from src.constants import AccountType # Enum for account types
from src.business_logic.account_manager import AccountManager
import logging

logger = logging.getLogger(__name__)

# --- Helper class for Tree Items (Nodes) ---
class TreeItem:
    def __init__(self, account_data: AccountEntity, parent_item=None):
        self.parent_item = parent_item
        self.account_data = account_data
        self.child_items: List['TreeItem'] = []

    def append_child(self, item: 'TreeItem'):
        self.child_items.append(item)

    def child(self, row: int) -> Optional['TreeItem']:
        if 0 <= row < len(self.child_items):
            return self.child_items[row]
        return None

    def child_count(self) -> int:
        return len(self.child_items)

    def column_count(self) -> int:
        return 2 # نام حساب و مانده

    def data(self, column: int) -> Any:
        if column == 0:
            return self.account_data.name
        if column == 1:
            balance = self.account_data.balance
            return f"{balance:,.0f}" if balance is not None else "0"
        return None

    def row(self) -> int:
        if self.parent_item:
            try:
                return self.parent_item.child_items.index(self)
            except ValueError:
                return 0
        return 0


# --- Custom Tree Model for Accounts ---
class AccountTreeModel(QAbstractItemModel):
    def __init__(self, account_manager: AccountManager, parent=None):
        super().__init__(parent)
        self.account_manager = account_manager
        self._headers = ["نام حساب", "مانده"]
        self.root_item = TreeItem(AccountEntity(id=0, name="Root", type=AccountType.ASSET))
        
    def setup_model_data(self, account_entities: List[AccountEntity], parent: TreeItem):
        """به صورت بازگشتی مدل را از روی ساختار درختی AccountEntity ها می‌سازد."""
        for entity in account_entities:
            new_item = TreeItem(entity, parent)
            parent.append_child(new_item)
            
            # FIX: بررسی .children به جای کلید "children"
            if hasattr(entity, 'children') and entity.children:
                self.setup_model_data(entity.children, new_item)

    def update_tree_data(self):
        """مدل را با واکشی داده‌های جدید از مدیر حساب‌ها، به‌روز می‌کند."""
        self.beginResetModel()
        self.root_item = TreeItem(AccountEntity(id=0, name="Root", type=AccountType.ASSET))
        
        # FIX: فراخوانی get_account_tree از آبجکت account_manager
        account_tree_data = self.account_manager.get_account_tree()
        
        self.setup_model_data(account_tree_data, self.root_item)
        self.endResetModel()
    
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent_item
        if parent_item == self.root_item or parent_item is None:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return item.data(index.column())
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None
# --- Add/Edit Account Dialog (Supports parent selection) ---
class AccountDialog(QDialog):
    def __init__(self, 
                 account_types: List[AccountType], 
                 potential_parents: List[AccountEntity], 
                 account: Optional[AccountEntity] = None, 
                 parent_widget=None): # Renamed 'parent' to 'parent_widget'
        super().__init__(parent_widget)
        self.account = account
        self.account_types_map = {at.value: at for at in account_types}
        self.potential_parents = potential_parents

        self.setWindowTitle("افزودن حساب جدید" if not account else f"ویرایش حساب: {account.name}")
        self.setMinimumWidth(400)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.name_edit = QLineEdit(self)
        self.type_combo = QComboBox(self)
        self.parent_combo = QComboBox(self)
        self.balance_spinbox = QDoubleSpinBox(self)
        
        self.balance_spinbox.setDecimals(2)
        self.balance_spinbox.setMinimum(-999999999.99)
        self.balance_spinbox.setMaximum(999999999.99)
        self.balance_spinbox.setGroupSeparatorShown(True)

        self.type_combo.addItems([at.value for at in account_types])

        self.parent_combo.addItem("-- حساب سطح بالا (بدون والد) --", None) 
        for acc_parent_candidate in self.potential_parents:
            if self.account and self.account.id == acc_parent_candidate.id:
                continue 
            self.parent_combo.addItem(f"{acc_parent_candidate.name} (ID: {acc_parent_candidate.id})", acc_parent_candidate.id)

        if self.account: 
            self.name_edit.setText(self.account.name)
            self.type_combo.setCurrentText(self.account.type.value)
            self.balance_spinbox.setValue(self.account.balance)
            self.balance_spinbox.setEnabled(False) # Balance not editable for existing accounts here
            
            if self.account.parent_id is None:
                self.parent_combo.setCurrentIndex(0)
            else:
                parent_index = self.parent_combo.findData(self.account.parent_id)
                if parent_index != -1:
                    self.parent_combo.setCurrentIndex(parent_index)
                else:
                    logger.warning(f"Parent ID {self.account.parent_id} for account {self.account.id} not found in parent_combo.")
                    self.parent_combo.setCurrentIndex(0) 
        else: 
            self.balance_spinbox.setEnabled(True)
            self.parent_combo.setCurrentIndex(0)

        layout.addRow("نام حساب:", self.name_edit)
        layout.addRow("نوع حساب:", self.type_combo)
        layout.addRow("حساب والد:", self.parent_combo)
        layout.addRow("مانده اولیه/فعلی:", self.balance_spinbox)
        
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
            QMessageBox.warning(self, "ورودی نامعتبر", "نام حساب نمی‌تواند خالی باشد.")
            return None
        
        selected_type_value = self.type_combo.currentText()
        account_type_enum = self.account_types_map.get(selected_type_value)
        if not account_type_enum:
            QMessageBox.critical(self, "خطا", "نوع حساب انتخاب شده نامعتبر است.")
            return None

        selected_parent_id = self.parent_combo.currentData()

        if self.account and self.account.id is not None and selected_parent_id == self.account.id:
            QMessageBox.warning(self, "ورودی نامعتبر", "یک حساب نمی‌تواند والد خودش باشد.")
            return None

        data = {
            "name": self.name_edit.text().strip(),
            "type": account_type_enum,
            "parent_id": selected_parent_id,
            "balance": self.balance_spinbox.value() if (not self.account or self.account.id is None) else (self.account.balance if self.account else 0.0)
        }
        return data

# --- Main Accounts UI Widget (Using QTreeView) ---
class AccountsUI(QWidget):
    def __init__(self, account_manager: AccountManager, parent=None):
        super().__init__(parent)
        self.account_manager = account_manager
        self.tree_model = AccountTreeModel(self.account_manager, self)
        
        self._init_ui()
        self.load_accounts_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.tree_view = QTreeView(self)
        self.tree_view.setModel(self.tree_model)
        
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        
        main_layout.addWidget(self.tree_view)

        header = self.tree_view.header()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # نام حساب
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # نوع
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # مانده
        
        main_layout.addWidget(self.tree_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("افزودن حساب جدید")
        self.edit_button = QPushButton("ویرایش حساب")
        self.delete_button = QPushButton("حذف حساب") 
        self.refresh_button = QPushButton("بارگذاری مجدد")
        self.expand_all_button = QPushButton("باز کردن همه")
        self.collapse_all_button = QPushButton("بستن همه")

        self.add_button.clicked.connect(self._open_add_account_dialog)
        self.edit_button.clicked.connect(self._open_edit_account_dialog)
        self.delete_button.clicked.connect(self._delete_selected_account)
        self.refresh_button.clicked.connect(self.load_accounts_data)
        self.expand_all_button.clicked.connect(self.tree_view.expandAll)
        self.collapse_all_button.clicked.connect(self.tree_view.collapseAll)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.expand_all_button)
        button_layout.addWidget(self.collapse_all_button)
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("AccountsUI initialized with QTreeView and buttons.")

    def load_accounts_data(self):
        """مدل درختی را با داده‌های جدید به‌روز می‌کند."""
        logger.debug("Loading accounts tree data...")
        try:
            # FIX: فراخوانی متد مدل بدون ارسال پارامتر
            self.tree_model.update_tree_data()
            self.tree_view.expandAll()
            logger.info("Account tree data loaded into model.")
        except Exception as e:
            logger.error(f"Error loading account tree: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری درخت حساب‌ها: {e}")


    def _get_selected_tree_item_data(self) -> Optional[Dict[str, Any]]:
        """Helper to get the account data dictionary from the selected tree item."""
        selection_model = self.tree_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            return None
        
        current_index = selection_model.currentIndex()
        if not current_index.isValid():
            return None
            
        tree_item_node = self.tree_model.get_item_from_index(current_index)
        if tree_item_node and isinstance(tree_item_node.account_data, dict):
            return tree_item_node.account_data
        return None

    def _open_add_account_dialog(self):
        logger.debug("Opening Add Account dialog for tree structure.")
        account_types_list = list(AccountType)
        potential_parents_list = self.account_manager.get_all_accounts() 
        
        dialog = AccountDialog(
            account_types_list,
            potential_parents=potential_parents_list,
            parent_widget=self # Corrected parent to parent_widget
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    self.account_manager.add_account(
                        name=data["name"],
                        account_type=data["type"],
                        parent_id=data.get("parent_id"), 
                        initial_balance=data["balance"] 
                    )
                    QMessageBox.information(self, "موفقیت", f"حساب '{data['name']}' با موفقیت اضافه شد.")
                    self.load_accounts_data() 
                except ValueError as ve: 
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error adding account: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در افزودن حساب: {e}")
            else:
                logger.debug("Add account dialog returned no data.")
        else:
            logger.debug("Add Account dialog cancelled.")

    def _open_edit_account_dialog(self):
        selected_account_data = self._get_selected_tree_item_data()
        if not selected_account_data:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک حساب را برای ویرایش انتخاب کنید.")
            return
        
        account_id_to_edit = selected_account_data.get("id")
        if account_id_to_edit is None:
            QMessageBox.critical(self, "خطا", "شناسه حساب برای ویرایش معتبر نیست.")
            return

        # Fetch the full AccountEntity for editing to ensure all fields are available if needed
        # and to pass the correct type to AccountDialog
        account_to_edit_entity = self.account_manager.get_account_by_id(account_id_to_edit)
        if not account_to_edit_entity:
            QMessageBox.critical(self, "خطا", f"حساب با شناسه {account_id_to_edit} برای ویرایش یافت نشد.")
            return

        logger.debug(f"Opening Edit Account dialog for Account ID: {account_to_edit_entity.id}.")
        account_types_list = list(AccountType)
        
        all_accounts_for_parent_selection = self.account_manager.get_all_accounts()
        potential_parents_list = [acc for acc in all_accounts_for_parent_selection if acc.id != account_to_edit_entity.id]

        dialog = AccountDialog(
            account_types_list,
            potential_parents=potential_parents_list, 
            account=account_to_edit_entity, 
            parent_widget=self # Corrected parent to parent_widget
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    new_parent_id = data.get("parent_id")
                    
                    updated_account = self.account_manager.update_account_details(
                        account_id=account_to_edit_entity.id, # type: ignore
                        name=data["name"],
                        account_type=data["type"],
                        parent_id=new_parent_id 
                    )
                    if updated_account:
                        QMessageBox.information(self, "موفقیت", f"حساب '{updated_account.name}' با موفقیت ویرایش شد.")
                        self.load_accounts_data()
                    else:
                         QMessageBox.warning(self, "هشدار", f"تغییری در حساب '{data['name']}' اعمال نشد یا حساب یافت نشد.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error editing account: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش حساب: {e}")
        
    def _delete_selected_account(self):
        selected_account_data = self._get_selected_tree_item_data()
        if not selected_account_data:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک حساب را برای حذف انتخاب کنید.")
            return

        account_id_to_delete = selected_account_data.get("id")
        account_name_to_delete = selected_account_data.get("name", "ناشناس")

        if account_id_to_delete is None:
            QMessageBox.critical(self, "خطا", "شناسه حساب برای حذف معتبر نیست.")
            return

        children = self.account_manager.get_child_accounts(account_id_to_delete)
        warning_message = ""
        if children:
            warning_message = (f"\nهشدار: این حساب دارای {len(children)} زیرمجموعه است. "
                               "پس از حذف، والد این زیرمجموعه‌ها NULL خواهد شد.")

        buttons_msg = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        reply = QMessageBox.question(self, "تایید حذف", 
                                     f"آیا از حذف حساب '{account_name_to_delete}' (شناسه: {account_id_to_delete}) مطمئن هستید؟"
                                     f"{warning_message}\nتوجه: اگر این حساب تراکنش داشته باشد، ممکن است حذف نشود.",
                                     buttons_msg, # type: ignore
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.debug(f"Attempting to delete Account ID: {account_id_to_delete}")
            try:
                success = self.account_manager.delete_account(account_id_to_delete)
                if success:
                    QMessageBox.information(self, "موفقیت", f"حساب '{account_name_to_delete}' با موفقیت حذف شد.")
                    self.load_accounts_data()
            except ValueError as ve:
                 QMessageBox.critical(self, "خطا در حذف", str(ve))
            except Exception as e:
                logger.error(f"Error deleting account: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در حذف حساب: {e}")