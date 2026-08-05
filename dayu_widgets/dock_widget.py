"""MDockWidget"""

# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets


class MDockWidget(QtWidgets.QDockWidget):
    """
    Just apply the qss. No more extend.
    """

    def __init__(self, title="", parent=None, flags=QtCore.Qt.Widget):
        super(MDockWidget, self).__init__(title, parent=parent, flags=flags)
