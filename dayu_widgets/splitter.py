# Import built-in modules
from functools import partial

# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.mixin import property_mixin


class _SplitterHandle(QtWidgets.QSplitterHandle):
    """QSplitterHandle 子类：让「双击均分」在 PySide 虚表生效。
    对实例 monkey-patch mouseDoubleClickEvent 在 PySide2/6 下不会进入虚表（功能是死代码）。"""

    def mouseDoubleClickEvent(self, event):
        splitter = self.parent()
        if hasattr(splitter, "setSizes"):
            splitter.setSizes([1 for _ in range(splitter.count())])
        super(_SplitterHandle, self).mouseDoubleClickEvent(event)


@property_mixin
class MSplitter(QtWidgets.QSplitter):
    def __init__(self, Orientation=QtCore.Qt.Horizontal, parent=None):
        super(MSplitter, self).__init__(Orientation, parent=parent)
        self.setHandleWidth(10)
        self.setProperty("animatable", True)
        self.setProperty("default_size", 100)
        self.setProperty("anim_move_duration", 300)
        dayu_theme.apply(self)

    def slot_splitter_click(self, index, first=True):
        size_list = self.sizes()
        if not 0 < index < len(size_list):
            return
        prev = index - 1
        prev_size = size_list[prev]
        next_size = size_list[index]
        default_size = self.property("default_size")
        if not prev_size:
            size_list[prev] = default_size
            size_list[index] -= default_size
        elif not next_size:
            size_list[index] = default_size
            size_list[prev] -= default_size
        else:
            if first:
                size_list[index] += prev_size
                size_list[prev] = 0
            else:
                size_list[prev] += next_size
                size_list[index] = 0

        if self.property("animatable"):
            anim = QtCore.QVariantAnimation(self)

            def anim_size(index, size_list, v):
                size_list[index - 1] += size_list[index] - v
                size_list[index] = v
                self.setSizes(size_list)

            anim.valueChanged.connect(partial(anim_size, index, size_list))
            anim.setDuration(self.property("anim_move_duration"))
            anim.setStartValue(next_size)
            anim.setEndValue(size_list[index])
            anim.start()
        else:
            self.setSizes(size_list)

    def createHandle(self):
        orient = self.orientation()
        is_horizontal = orient is QtCore.Qt.Horizontal
        handle = _SplitterHandle(orient, self)

        # NOTES: double click average size（已由 _SplitterHandle 类实现）

        layout = QtWidgets.QVBoxLayout() if is_horizontal else QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        handle.setLayout(layout)

        def make_slot(button, first):
            def slot(*_):
                # 点击时动态计算当前 handle 的索引，范围 1 ~ count-1
                index = self._handle_index(handle)
                if index is not None:
                    self.slot_splitter_click(index, first)

            return slot

        button = QtWidgets.QToolButton(handle)
        button.setArrowType(QtCore.Qt.LeftArrow if is_horizontal else QtCore.Qt.UpArrow)
        button.clicked.connect(make_slot(button, True))
        layout.addWidget(button)
        button = QtWidgets.QToolButton(handle)
        arrow = QtCore.Qt.RightArrow if is_horizontal else QtCore.Qt.DownArrow
        button.setArrowType(arrow)
        button.clicked.connect(make_slot(button, False))
        layout.addWidget(button)

        return handle

    def _handle_index(self, handle):
        # QSplitter 的 handle 从 0 开始编号：handle(i) 分隔 widget i 与 i+1
        # slot_splitter_click 的 index 语义是"边界右侧的 widget 序号"，故返回 i + 1
        for i in range(self.count()):
            if self.handle(i) is handle:
                return i + 1
        return None
