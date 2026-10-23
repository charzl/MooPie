"""Desktop palettes and styles, shared by both appearance modes."""
STYLE = '''
QWidget {background:#101116;color:#e4e7ef;font-size:13px;font-family:"Noto Sans SC";}
QLabel#eyebrow {color:#8c9ab3;font-size:11px;font-weight:bold;}
QLabel#title {font-size:27px;font-weight:bold;}
QLabel#scopeHeading {font-size:20px;font-weight:bold;}
QLabel#efficiencyValue {font-size:30px;font-weight:bold;}
QLabel#muted {color:#949bad;font-size:12px;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:#1b1f28;border:1px solid #303542;border-radius:8px;padding:9px;}
QComboBox {padding-left:12px;padding-right:38px;}
QComboBox::drop-down {subcontrol-origin:padding;subcontrol-position:top right;width:30px;border:0;}
QComboBox[vectorArrow="true"]::down-arrow {image:none;width:0;height:0;}
QListWidget#symbolSuggestions {background:#191c24;color:#e4e7ef;border:1px solid #465576;border-radius:8px;}
QListWidget#symbolSuggestions::item {padding:7px 12px;}
QListWidget#symbolSuggestions::item:selected {background:#303b55;}
QComboBox QAbstractItemView {background:#1b1f28;color:#e4e7ef;selection-background-color:#303b55;}
QTabWidget::pane {border:0;}
QTabBar::tab {background:#101116;color:#949bad;padding:8px 20px;border-bottom:2px solid transparent;}
QTabBar::tab:selected {color:#e4e7ef;border-bottom:2px solid #8b9bff;}
QTabBar::tab:hover {color:#e4e7ef;}
QTabBar#workspaceNavigation::tab {font-size:16px;font-weight:bold;padding:8px 28px;}
QPushButton,QToolButton {background:#1b1f28;border:1px solid #303542;border-radius:10px;padding:10px 18px;font-weight:bold;}
QPushButton:hover,QToolButton:hover {background:#293142;}
QPushButton[compact="true"],QToolButton[compact="true"] {padding:6px 12px;}
QToolButton[menuOnly="true"] {padding-right:34px;}
QToolButton[menuOnly="true"]::menu-indicator {subcontrol-origin:padding;subcontrol-position:right center;right:12px;width:12px;height:12px;}
QToolButton[splitMenu="true"] {padding-right:36px;}
QToolButton[splitMenu="true"]::menu-button {width:24px;background:#1b1f28;border-left:1px solid #303542;border-top-right-radius:10px;border-bottom-right-radius:10px;}
QToolButton[splitMenu="true"]::menu-arrow {width:10px;height:10px;}
QPushButton#primary {background:#e8ebf3;color:#141820;border:0;}
QPushButton#primary:hover {background:#cfd9ef;}
QPushButton:disabled,QToolButton:disabled {background:#1b1f28;color:#626c80;}
QMenu {background:#1b1f28;border:1px solid #303542;padding:6px;}
QMenu::item {padding:9px 18px;border-radius:5px;}
QMenu::item:selected {background:#303b55;}
QMenu::item:disabled {color:#626c80;}
QMenu::separator {height:1px;background:#303542;margin:5px 8px;}
QMenu[preferencesMenu="true"] {font-size:14px;padding:8px;}
QMenu[preferencesMenu="true"]::item {padding:10px 38px 10px 34px;}
QMenu[preferencesMenu="true"]::indicator {width:14px;height:14px;}
QTextBrowser {background:#191c24;border:1px solid #2c313c;border-radius:12px;padding:18px;font-size:14px;}
QFrame#rankingCard {background:#191c24;border:1px solid #2c313c;border-radius:14px;}
QFrame#rankingCard QLabel {background:transparent;}
QFrame#scopePanel {background:#191c24;border:1px solid #2c313c;border-radius:12px;}
QFrame#scopePanel QLabel {background:transparent;}
QListWidget#scopeList {background:#191c24;border:0;outline:0;}
QListWidget#scopeList::item {padding:10px 12px;border-radius:6px;}
QListWidget#scopeList::item:selected {background:#303b55;}
QListWidget#scopeList::item:hover {background:#202632;}
QFrame#firstChoice {background:#202632;border:0;border-radius:12px;}
QLabel#firstChoiceTitle {font-size:18px;font-weight:bold;}
QLabel#cardTitle {font-size:17px;font-weight:bold;}
QLabel#badge {color:#e9b45f;background:#352b1d;border:1px solid #654b25;border-radius:12px;padding:5px 12px;font-size:11px;}
QLabel#dataState {color:#8da89d;font-size:12px;}
QTableWidget {background:#191c24;border:0;outline:0;selection-background-color:#252e42;selection-color:#e4e7ef;}
QTableWidget::item {border-bottom:1px solid #2b303a;padding:9px 8px;}
QTableWidget::item:selected {background:#252e42;}
QTableWidget::item:hover {background:#202632;}
QHeaderView {background:#171a21;}
QHeaderView::section {background:#171a21;color:#929bad;border:0;border-top:1px solid #2c313c;border-bottom:1px solid #2c313c;padding:12px 8px;text-align:left;font-size:11px;}
QTableCornerButton::section {background:#171a21;border:0;}
QScrollBar:vertical {background:#191c24;width:8px;}
QScrollBar:horizontal {background:#191c24;height:8px;}
QScrollBar::handle {background:#3d4556;border-radius:4px;min-height:24px;min-width:24px;}
QScrollBar::add-line,QScrollBar::sub-line {width:0;height:0;}
'''

DARK = dict(window='#101116', surface='#191c24', text='#e4e7ef', muted='#949bad',
            accent='#80adff', warning='#e9b45f', selected='#252e42', track='#2c313d')
LIGHT = dict(window='#f4f6fa', surface='#ffffff', text='#202938', muted='#58677b',
             accent='#215fbb', warning='#936000', selected='#dce8fb', track='#d4dce8')
LIGHT_REPLACEMENTS = {
    '#101116':'#f4f6fa', '#e4e7ef':'#202938', '#8c9ab3':'#596b84', '#949bad':'#58677b',
    '#1b1f28':'#ffffff', '#303542':'#c9d2df', '#191c24':'#ffffff', '#465576':'#879ab8',
    '#303b55':'#dce8fb', '#8b9bff':'#5369c8', '#293142':'#e7edf7',
    '#e8ebf3':'#253f78', '#141820':'#ffffff', '#cfd9ef':'#34568e', '#626c80':'#778294',
    '#2c313c':'#cfd7e3', '#e9b45f':'#936000', '#352b1d':'#fff3d9', '#654b25':'#d6b978',
    '#8da89d':'#35684f', '#252e42':'#dce8fb', '#2b303a':'#e1e6ee', '#202632':'#edf2fa',
    '#171a21':'#edf1f7', '#929bad':'#526178', '#3d4556':'#a2aec0',
}


def stylesheet(theme):
    if theme == 'dark': return STYLE
    import re
    return re.sub(r'#[0-9a-f]{6}', lambda m:LIGHT_REPLACEMENTS.get(m[0],m[0]), STYLE)
