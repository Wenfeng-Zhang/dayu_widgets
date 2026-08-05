# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets.mixin import cursor_mixin
from dayu_widgets.mixin import stacked_animation_mixin


@cursor_mixin
class MTabBar(QtWidgets.QTabBar):
    def __init__(self, parent=None):
        super(MTabBar, self).__init__(parent=parent)
        self.setDrawBase(False)

    def tabSizeHint(self, index):
        tab_text = self.tabText(index)
        try:
            text_width = self.fontMetrics().horizontalAdvance(tab_text)
        except AttributeError:
            text_width = self.fontMetrics().width(tab_text)
        if self.tabsClosable():
            return QtCore.QSize(
                text_width + 70,
                self.fontMetrics().height() + 20,
            )
        else:
            return QtCore.QSize(
                text_width + 50,
                self.fontMetrics().height() + 20,
            )


@stacked_animation_mixin
class MTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(MTabWidget, self).__init__(parent=parent)
        self.bar = MTabBar()
        self.setTabBar(self.bar)

    def disable_animation(self):
        self.currentChanged.disconnect(self._play_anim)
