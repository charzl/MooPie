"""Persisted presentation settings; switching them never reruns research."""
from PySide6.QtCore import QObject, Qt, QSettings
from PySide6.QtGui import QAction, QPalette, QColor, QGuiApplication
from PySide6.QtWidgets import (QWidget, QLabel, QAbstractButton, QComboBox, QTabWidget,
                              QLineEdit, QTextBrowser, QTableWidget, QListWidget)
from .desktop_theme import DARK, LIGHT, stylesheet
from .desktop_translations import english

SOURCE_ROLE = Qt.ItemDataRole.UserRole + 197


class DesktopPreferences(QObject):
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings or QSettings('MooClients', 'Research')
        self.language = self.settings.value('ui_language', 'zh')
        if self.language not in ('zh', 'en'): self.language='zh'
        self.theme = self.settings.value('ui_theme', 'system')
        if self.theme not in ('dark', 'light', 'system'): self.theme='system'
        self.root = None
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.system_scheme_changed)

    @property
    def effective_theme(self):
        if self.theme != 'system': return self.theme
        return 'dark' if QGuiApplication.styleHints().colorScheme()==Qt.ColorScheme.Dark else 'light'

    @property
    def colors(self): return DARK if self.effective_theme=='dark' else LIGHT

    def translate(self, source): return english(source) if self.language=='en' else source

    def set_text(self, target, source, method='setText'):
        target.setProperty('_ui_source_'+method, source)
        value=self.translate(source)
        if method=='setHtml' and self.effective_theme=='light': value=value.replace('#9aaab7','#58677b')
        scroll = target.verticalScrollBar().value() if isinstance(target,QTextBrowser) else None
        getattr(target,method)(value)
        if scroll is not None: target.verticalScrollBar().setValue(scroll)

    def localize_list(self, widget, fresh=False):
        for index in range(widget.count()):
            item=widget.item(index)
            source=item.text() if fresh or item.data(SOURCE_ROLE) is None else item.data(SOURCE_ROLE)
            item.setData(SOURCE_ROLE,source); item.setText(self.translate(source))

    def localize_table(self, widget, fresh=False):
        items=[widget.horizontalHeaderItem(i) for i in range(widget.columnCount())]
        items += [widget.item(r,c) for r in range(widget.rowCount()) for c in range(widget.columnCount())]
        for item in items:
            if item is None: continue
            for offset, getter, setter in [(0,'text','setText'),(1,'toolTip','setToolTip')]:
                role=SOURCE_ROLE+offset
                source=getattr(item,getter)() if fresh or item.data(role) is None else item.data(role)
                item.setData(role,source); getattr(item,setter)(self.translate(source))
        if hasattr(widget,'apply_colors'): widget.apply_colors(self.colors)

    def localize_tree(self, root):
        for target in [root,*root.findChildren(QWidget),*root.findChildren(QAction)]:
            methods=[('toolTip','setToolTip'),('accessibleName','setAccessibleName')]
            if isinstance(target,(QLabel,QAbstractButton,QAction)): methods.append(('text','setText'))
            if target is root or target.isWidgetType() and target.isWindow(): methods.append(('windowTitle','setWindowTitle'))
            if isinstance(target,QLineEdit): methods.append(('placeholderText','setPlaceholderText'))
            if isinstance(target,QTextBrowser): methods.append(('toHtml','setHtml'))
            for getter,setter in methods:
                if not hasattr(target,getter): continue
                source=target.property('_ui_source_'+setter)
                if source is None: source=getattr(target,getter)()
                if source: self.set_text(target,source,setter)
            if isinstance(target,QComboBox) and not target.property('i18nSkipItems'):
                blocked=target.blockSignals(True)
                for index in range(target.count()):
                    source=target.itemData(index,SOURCE_ROLE)
                    if source is None: source=target.itemText(index); target.setItemData(index,source,SOURCE_ROLE)
                    target.setItemText(index,self.translate(source))
                target.blockSignals(blocked)
            if isinstance(target,QTabWidget):
                for index in range(target.count()):
                    page=target.widget(index); source=page.property('_ui_tab_source')
                    if source is None: source=target.tabText(index); page.setProperty('_ui_tab_source',source)
                    target.setTabText(index,self.translate(source))
            if isinstance(target,QListWidget): self.localize_list(target)
            if isinstance(target,QTableWidget): self.localize_table(target)

    def set_language(self, value):
        if value not in ('zh','en'): raise ValueError('Unsupported UI language')
        self.language=value; self.settings.setValue('ui_language',value)
        if self.root: self.localize_tree(self.root)

    def set_theme(self, value):
        if value not in ('dark','light','system'): raise ValueError('Unsupported appearance')
        self.theme=value; self.settings.setValue('ui_theme',value)
        self.apply_theme()

    def system_scheme_changed(self, _scheme):
        if self.theme=='system': self.apply_theme()

    def apply_theme(self):
        if self.root is None: return
        colors=self.colors
        palette=QPalette(self.root.palette())
        for role,color in [(QPalette.Window,colors['window']),(QPalette.WindowText,colors['text']),
                           (QPalette.Base,colors['surface']),(QPalette.AlternateBase,colors['window']),
                           (QPalette.Text,colors['text']),(QPalette.Button,colors['surface']),
                           (QPalette.ButtonText,colors['text']),(QPalette.Highlight,colors['selected']),
                           (QPalette.HighlightedText,colors['text']),(QPalette.ToolTipBase,colors['surface']),
                           (QPalette.ToolTipText,colors['text']),(QPalette.Link,colors['accent'])]:
            palette.setColor(role,QColor(color))
        self.root.setPalette(palette)
        self.root.setProperty('effectiveTheme',self.effective_theme)
        self.root.setStyleSheet(stylesheet(self.effective_theme))
        self.localize_tree(self.root)
