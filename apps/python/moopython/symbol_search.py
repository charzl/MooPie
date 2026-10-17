"""Native, local-only stock suggestions; selection never starts market research."""
from PySide6.QtCore import QObject, QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QToolTip

from .security_directory import SecurityDirectory
from .watchlist import normalize_stock
from .symbol_favorites import SuggestionDelegate, WatchlistAdder, favorite_rect


class SymbolSuggestions(QObject):
    watchlist_changed = Signal()
    status = Signal(str)

    def __init__(self, field, parent, directory=None):
        super().__init__(parent)
        self.field = field
        self.ui = parent.ui
        self.directory = directory or SecurityDirectory()
        self.owner = parent
        self.members = set()
        self.heart_pressed = None
        self.adder = WatchlistAdder(parent)
        self.adder.completed.connect(self.added)
        self.adder.failed.connect(self.add_failed)
        self.view = QListWidget(parent)
        self.view.setObjectName('symbolSuggestions')
        self.view.setAccessibleName('股票代码及公司名称候选')
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.setMaximumHeight(190)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setItemDelegate(SuggestionDelegate(self))
        self.view.viewport().installEventFilter(self)
        self.view.viewport().setMouseTracking(True)
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
            self.refresh_membership()
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
        self.ui.localize_list(self.view,fresh=True)
        self.view.show()

    def refresh_membership(self):
        self.members = set(self.owner.watchlist.symbols())
        self.view.viewport().update()

    def favorite(self, code):
        if code in self.members or self.adder.process is not None: return
        self.adder.add(code)
        self.status.emit(code+' · 正在加入 Watchlist…')
        self.view.viewport().update()

    def added(self, result):
        self.refresh_membership()
        self.watchlist_changed.emit()
        self.status.emit(result['symbol']+' 已加入 Watchlist。')

    def add_failed(self, error):
        self.refresh_membership()
        self.status.emit('未加入 Watchlist：'+error)

    def shutdown(self):
        self.timer.stop(); self.adder.shutdown()

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
            self.ui.set_text(self.field,'已选择：' + row['name'] + '（' + row['code'] + '）','setToolTip')
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
        if watched is self.view.viewport():
            kind = event.type()
            if kind in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease,QEvent.Type.MouseButtonDblClick,QEvent.Type.ToolTip):
                pos = event.pos() if kind==QEvent.Type.ToolTip else event.position().toPoint()
                item = self.view.itemAt(pos)
                row = item.data(Qt.ItemDataRole.UserRole) if item else None
                hit = row and favorite_rect(self.view.visualItemRect(item)).contains(pos)
                if kind==QEvent.Type.ToolTip and hit:
                    text = ('已在 Watchlist 中；可在「管理 Watchlist」中移除。' if row['code'] in self.members else
                            '正在加入 Watchlist…' if self.adder.process is not None else '加入 Watchlist')
                    QToolTip.showText(event.globalPos(),self.ui.translate(text),self.view); return True
                if kind==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton and hit:
                    self.heart_pressed=row['code']; return True
                if kind==QEvent.Type.MouseButtonRelease and self.heart_pressed is not None:
                    code=self.heart_pressed; self.heart_pressed=None
                    if hit and row['code']==code: self.favorite(code)
                    return True
                if kind==QEvent.Type.MouseButtonDblClick and hit: return True
        if watched is self.field and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key==Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier and self.view.isVisible() and self.rows:
                self.favorite(self.view.currentItem().data(Qt.ItemDataRole.UserRole)['code']); return True
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
