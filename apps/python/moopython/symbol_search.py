"""Native, local-only stock suggestions; selection never starts market research."""
from PySide6.QtCore import QObject, QEvent, Qt, QTimer
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from .security_directory import SecurityDirectory
from .watchlist import normalize_stock


class SymbolSuggestions(QObject):
    def __init__(self, field, parent, directory=None):
        super().__init__(parent)
        self.field = field
        self.directory = directory or SecurityDirectory()
        self.view = QListWidget(parent)
        self.view.setObjectName('symbolSuggestions')
        self.view.setAccessibleName('股票代码及公司名称候选')
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.setMaximumHeight(190)
        self.view.hide()
        self.rows = []
        self.selecting = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self.update)
        field.textChanged.connect(self.edited)
        field.installEventFilter(self)
        self.view.itemClicked.connect(self.choose)

    def edited(self, _text):
        if self.selecting: return
        self.field.setToolTip('')
        self.dismiss()
        if self.field.text().strip() and self.field.isEnabled(): self.timer.start()

    def dismiss(self):
        self.timer.stop()
        self.view.hide()
        self.rows = []

    def update(self):
        text = self.field.text().strip()
        if not text or not self.field.isEnabled():
            self.dismiss(); return
        self.view.clear()
        try:
            self.rows = self.directory.search(text)
            if self.rows:
                for row in self.rows:
                    label = f'{row["code"].removeprefix("US.")}   ·   {row["name"]}   ·   {row["security_type"]}'
                    if row['matched_alias']: label += '   ·   别名：' + row['matched_alias']
                    item = QListWidgetItem(label)
                    item.setData(Qt.ItemDataRole.UserRole, row)
                    item.setToolTip(row['code'] + ' · ' + row['name'])
                    self.view.addItem(item)
                self.view.setCurrentRow(0)
            else:
                note = ('尚未建立股票目录，请点击「更新股票目录」。' if not self.directory.status()['securities']
                        else '没有匹配项。可尝试名称前缀或 *关键词*；仍可输入完整股票代码。')
                self.message(note)
        except (ValueError, RuntimeError, OSError) as error:
            self.rows = []
            self.message('目录查询失败：' + str(error))
        self.view.setFixedHeight(min(190, max(44, self.view.count() * 36 + 6)))
        self.view.show()

    def message(self, text):
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.view.addItem(item)

    def choose(self, item):
        row = item.data(Qt.ItemDataRole.UserRole)
        if not row: return
        self.selecting = True
        try:
            self.field.setText(row['code'].removeprefix('US.'))
            self.field.setToolTip('已选择：' + row['name'] + '（' + row['code'] + '）')
        finally: self.selecting = False
        self.dismiss()
        self.field.setFocus()

    def query_code(self):
        text = self.field.text().strip()
        if not text: return None
        rows = self.directory.search(text)
        try: code = normalize_stock(text)
        except ValueError:
            code = None
        if rows and not any(row['code'] == code for row in rows):
            self.update()
            raise ValueError('请先从输入框下方选择具体股票，再查询或加入 Watchlist。')
        if code is None or '*' in text or '?' in text:
            self.update()
            raise ValueError('请输入完整股票代码，或从下方候选中选择股票。')
        return code

    def eventFilter(self, watched, event):
        if watched is self.field and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.dismiss(); return True
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                if not self.view.isVisible(): self.update()
                if self.rows:
                    current = self.view.currentRow()
                    self.view.setCurrentRow(max(0, min(len(self.rows)-1, current + (1 if key == Qt.Key.Key_Down else -1))))
                    return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.view.isVisible() and self.rows:
                self.choose(self.view.currentItem()); return True
        return super().eventFilter(watched, event)
