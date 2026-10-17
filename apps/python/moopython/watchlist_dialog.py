"""Stage Watchlist removals locally; only explicit confirmation writes SQLite."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QAbstractItemView)
from .desktop_preferences import DesktopPreferences


class WatchlistDialog(QDialog):
    def __init__(self, watchlist, parent=None):
        super().__init__(parent)
        self.ui = parent.ui if parent and hasattr(parent,'ui') else DesktopPreferences(parent=self)
        self.watchlist = watchlist
        self.pending = {}
        self.removal_result = None
        self.setWindowTitle('管理 Watchlist')
        self.resize(600, 480)
        layout = QVBoxLayout(self)
        self.heading = QLabel('Watchlist')
        layout.addWidget(self.heading)
        note = QLabel('选择股票后点「删除选中」，再点「确认保存」生效；取消则保留原名单。')
        note.setWordWrap(True); layout.addWidget(note)
        self.items = QListWidget()
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.items.setAccessibleName('Watchlist 股票名单')
        for row in watchlist.status()['items']:
            item = QListWidgetItem(row['symbol'].removeprefix('US.') + '  ·  ' + (row['name'] or '公司名暂未收录'))
            item.setData(Qt.ItemDataRole.UserRole, row)
            self.items.addItem(item)
        layout.addWidget(self.items, 1)
        self.message = QLabel(''); self.message.setWordWrap(True); layout.addWidget(self.message)
        buttons = QHBoxLayout()
        self.remove_button = QPushButton('删除选中')
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.stage_removal)
        self.items.itemSelectionChanged.connect(lambda: self.remove_button.setEnabled(bool(self.items.selectedItems())))
        buttons.addWidget(self.remove_button); buttons.addStretch()
        self.cancel_button = QPushButton('取消'); self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        self.confirm_button = QPushButton('确认保存')
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.save)
        buttons.addWidget(self.confirm_button)
        layout.addLayout(buttons)
        self.update_heading()
        self.ui.localize_tree(self)

    def update_heading(self):
        self.ui.set_text(self.heading,f'Watchlist · {self.items.count()} 只股票')

    def stage_removal(self):
        for item in self.items.selectedItems():
            row = item.data(Qt.ItemDataRole.UserRole)
            self.pending[row['id']] = row['symbol']
            self.items.takeItem(self.items.row(item))
        self.ui.set_text(self.message,'待删除：' + '、'.join(self.pending.values()) + '。点击「确认保存」后生效。')
        self.confirm_button.setEnabled(bool(self.pending))
        self.update_heading()

    def save(self):
        try:
            self.removal_result = self.watchlist.remove_items(self.pending)
        except (ValueError, RuntimeError, OSError) as error:
            self.ui.set_text(self.message,'保存失败，尚未确认删除：' + str(error))
            return
        self.accept()
