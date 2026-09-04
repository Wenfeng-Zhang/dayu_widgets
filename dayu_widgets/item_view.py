# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets
from functools import partial

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets import utils
from dayu_widgets.header_view import MHeaderView
from dayu_widgets.item_model import MTableModel
from dayu_widgets.menu import MMenu
from dayu_widgets.qt import MPixmap
from dayu_widgets.qt import get_scale_factor


HEADER_SORT_MAP = {"asc": QtCore.Qt.AscendingOrder, "desc": QtCore.Qt.DescendingOrder}


def draw_empty_content(view, text=None, pix_map=None):
    pix_map = pix_map or MPixmap("empty.svg")
    text = text or view.tr("No Data")
    painter = QtGui.QPainter(view)
    font_metrics = painter.fontMetrics()
    painter.setPen(QtGui.QPen(QtGui.QColor(dayu_theme.secondary_text_color)))
    content_height = pix_map.height() + font_metrics.height()
    padding = 10
    proper_min_size = min(
        view.height() - padding * 2,
        view.width() - padding * 2,
        content_height
    )
    if proper_min_size < content_height:
        height = proper_min_size - font_metrics.height()
        pix_map = pix_map.scaledToHeight(height, QtCore.Qt.SmoothTransformation)
        content_height = proper_min_size

    try:
        text_width = font_metrics.horizontalAdvance(text)
    except AttributeError:
        text_width = font_metrics.width(text)

    painter.drawText(
        view.width() / 2 - text_width / 2,
        view.height() / 2 + content_height / 2 - font_metrics.height() / 2,
        text,
    )
    painter.drawPixmap(
        view.width() / 2 - pix_map.width() / 2,
        view.height() / 2 - content_height / 2,
        pix_map,
    )
    painter.end()


class MOptionDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(MOptionDelegate, self).__init__(parent)
        self.editor = None
        self.showed = False
        self.exclusive = True
        self.parent_widget = None
        self.arrow_space = 20
        self.arrow_height = 6

    def set_exclusive(self, flag):
        self.exclusive = flag

    def createEditor(self, parent, option, index):
        self.parent_widget = parent
        self.editor = MMenu(exclusive=self.exclusive, parent=parent)
        self.editor.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        model = utils.real_model(index)
        real_index = utils.real_index(index)
        data_obj = real_index.internalPointer()
        column = real_index.column()
        if (
            model is None
            or not getattr(model, "header_list", None)
            or column < 0
            or column >= len(model.header_list)
        ):
            return None
        attr = "{}_list".format(model.header_list[column].get("key"))

        self.editor.set_data(utils.get_obj_value(data_obj, attr, []))
        self.editor.sig_value_changed.connect(self._slot_finish_edit)
        return self.editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.EditRole)
        # EditRole 为 None 时用空列表兜底，避免 MMenu.set_value 的类型断言崩溃
        editor.set_value(value if value is not None else [])

    def setModelData(self, editor, model, index):
        model.setData(index, editor.property("value"))

    def updateEditorGeometry(self, editor, option, index):
        point = QtCore.QPoint(option.rect.x(), option.rect.y() + option.rect.height())
        editor.move(self.parent_widget.mapToGlobal(point))

    def paint(self, painter, option, index):
        painter.save()
        icon_color = dayu_theme.icon_color
        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.fillRect(option.rect, QtGui.QColor(dayu_theme.primary_5))
            icon_color = "#fff"
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, QtGui.QColor(dayu_theme.primary_6))
            icon_color = "#fff"
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.white))
        pix = MPixmap("down_fill.svg", icon_color)
        h = option.rect.height()
        pix = pix.scaledToWidth(h * 0.5, QtCore.Qt.SmoothTransformation)
        painter.drawPixmap(option.rect.x() + option.rect.width() - h, option.rect.y() + h / 4, pix)
        painter.restore()
        super(MOptionDelegate, self).paint(painter, option, index)

    @QtCore.Slot(object)
    def _slot_finish_edit(self, obj):
        self.commitData.emit(self.editor)

    def sizeHint(self, option, index):
        orig = super(MOptionDelegate, self).sizeHint(option, index)
        return QtCore.QSize(orig.width() + self.arrow_space, orig.height())

    # def eventFilter(self, obj, event):
    #     if obj is self.editor:
    #         print event.type(), obj.size()
    #     return super(MOptionDelegate, self).eventFilter(obj, event)


def set_header_list(self, header_list):
    scale_x, _ = get_scale_factor()
    self.header_list = header_list
    if self.header_view:
        has_explicit_order = False
        for index, i in enumerate(header_list):
            self.header_view.setSectionHidden(index, i.get("hide", False))
            self.header_view.resizeSection(index, i.get("width", 100) * scale_x)
            if "order" in i:
                has_explicit_order = True
                order = i.get("order")
                if order in HEADER_SORT_MAP.values():
                    self.header_view.setSortIndicator(index, order)
                elif order in HEADER_SORT_MAP:
                    self.header_view.setSortIndicator(index, HEADER_SORT_MAP[order])
            if i.get("selectable", False):
                delegate = MOptionDelegate(parent=self)
                delegate.set_exclusive(i.get("exclusive", True))
                self.setItemDelegateForColumn(index, delegate)
            elif self.itemDelegateForColumn(index):
                self.setItemDelegateForColumn(index, None)
        # 无显式排序配置时，把初始排序指示器设为升序（与数据默认顺序一致）。
        # Qt 的 setSortingEnabled(True) 默认初始指示器为 0/Descending，
        # 若数据是升序，首次点击会把方向翻到 Ascending 导致"点了没反应"。
        if not has_explicit_order:
            self.header_view.setSortIndicator(0, QtCore.Qt.AscendingOrder)


def enable_context_menu(self, enable):
    if enable:
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # 防止重复调用时重复 connect 导致一次右键多次发射
        utils.safe_disconnect(self.customContextMenuRequested, self.slot_context_menu)
        self.customContextMenuRequested.connect(self.slot_context_menu)
    else:
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)


# @QtCore.Slot(QtCore.QModelIndex)
def slot_lift_menu(self, modelIndex):
    if modelIndex.isValid():
        need_map = isinstance(self.model(), QtCore.QSortFilterProxyModel)
        selection = []
        for index in (
            self.selectionModel().selectedRows()
            or self.selectionModel().selectedIndexes()
        ):
            data_obj = (
                self.model().mapToSource(index).internalPointer()
                if need_map
                else index.internalPointer()
            )
            selection.append(data_obj)
        event = utils.ItemViewMenuEvent(view=self, selection=selection, extra={})
        self.sig_left_menu.emit(event)
    else:
        event = utils.ItemViewMenuEvent(view=self, selection=[], extra={})
        self.sig_left_menu.emit(event)


@QtCore.Slot(QtCore.QPoint)
def slot_context_menu(self, point):
    proxy_index = self.indexAt(point)
    if proxy_index.isValid():
        need_map = isinstance(self.model(), QtCore.QSortFilterProxyModel)
        selection = []
        selected = (
            self.selectionModel().selectedRows()
            or self.selectionModel().selectedIndexes()
        )
        for index in selected:
            if need_map:
                source_index = self.model().mapToSource(index)
                data_obj = source_index.internalPointer()
            else:
                data_obj = index.internalPointer()
            selection.append(data_obj)
        event = utils.ItemViewMenuEvent(view=self, selection=selection, extra={})
        self.sig_context_menu.emit(event)
    else:
        event = utils.ItemViewMenuEvent(view=self, selection=[], extra={})
        self.sig_context_menu.emit(event)


def mouse_move_event(self, event):
    index = self.indexAt(event.pos())
    real_index = utils.real_index(index)
    column = real_index.column()
    row = real_index.row()
    if (
        column != -1
        and row != -1
        and self.header_list
        and column < len(self.header_list)
        and self.header_list[column].get("is_link", False)
    ):
        key_name = self.header_list[column]["key"]
        data_list = utils.real_model(self.model()).get_data_list()
        if data_list and 0 <= row < len(data_list):
            data_obj = data_list[row]
            value = utils.get_obj_value(data_obj, key_name)
            if value:
                self.setCursor(QtCore.Qt.PointingHandCursor)
                return
    self.setCursor(QtCore.Qt.ArrowCursor)


def mouse_release_event(self, event):
    if event.button() != QtCore.Qt.LeftButton:
        return
    index = self.indexAt(event.pos())
    real_index = utils.real_index(index)
    column = real_index.column()
    if (
        column != -1
        and self.header_list
        and column < len(self.header_list)
        and self.header_list[column].get("is_link", False)
    ):
        key_name = self.header_list[column]["key"]
        data_obj = real_index.internalPointer()
        value = utils.get_obj_value(data_obj, key_name)
        if value:
            if isinstance(value, (list, dict)):
                self.sig_link_clicked.emit(value)
            elif isinstance(value, str):
                try:
                    if data_obj.get('_parent'):
                        del data_obj['_parent']
                except: pass
                self.sig_link_clicked.emit(data_obj)


class MTableView(QtWidgets.QTableView):
    set_header_list = set_header_list
    enable_context_menu = enable_context_menu
    slot_context_menu = slot_context_menu
    sig_context_menu = QtCore.Signal(object)
    slot_left_menu = slot_lift_menu
    sig_left_menu = QtCore.Signal(object)
    sig_link_clicked = QtCore.Signal(object)

    def __init__(self, size=None, show_row_count=False, parent=None):
        super(MTableView, self).__init__(parent)
        self._no_data_image = None
        self._no_data_text = self.tr("No Data")
        size = size or dayu_theme.default_size
        ver_header_view = MHeaderView(QtCore.Qt.Vertical, parent=self, show_sort_indicator=False)
        ver_header_view.setDefaultSectionSize(size)
        ver_header_view.setSortIndicatorShown(False)
        self.setVerticalHeader(ver_header_view)
        self.header_list = []
        self.header_view = MHeaderView(QtCore.Qt.Horizontal, parent=self)
        self.header_view.setFixedHeight(size)
        if not show_row_count:
            ver_header_view.hide()
        self.setHorizontalHeader(self.header_view)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)

        self.pressed.connect(self.slot_left_menu)

    def set_no_data_text(self, text):
        self._no_data_text = text

    def set_no_data_image(self, image):
        self._no_data_image = image

    def setShowGrid(self, flag):
        self.header_view.setProperty("grid", flag)
        self.verticalHeader().setProperty("grid", flag)
        self.header_view.style().polish(self.header_view)

        return super(MTableView, self).setShowGrid(flag)

        # setting = {
        #     'key': attr,  # 必填，用来读取 model后台数据结构的属性
        #     'label': attr.title(),  # 选填，显示在界面的该列的名字
        #     'width': 100,  # 选填，单元格默认的宽度
        #     'default_filter': False,  # 选填，如果有组合的filter组件，该属性默认是否显示，默认False
        #     'searchable': False,  # 选填，如果有搜索组件，该属性是否可以被搜索，默认False
        #     'editable': False,  # 选填，该列是否可以双击编辑，默认False
        #     'selectable': False,  # 选填，该列是否可以双击编辑，且使用下拉列表选择。该下拉框的选项们，是通过 data 拿数据的
        #     'checkable': False,  # 选填，该单元格是否要加checkbox，默认False
        #     'exclusive': True,  # 配合selectable，如果是可以多选的则为 False，如果是单选，则为True
        #     'order': None,  # 选填，初始化时，该列的排序方式, 0 升序，1 降序
        #     # 下面的是每个单元格的设置，主要用来根据本单元格数据，动态设置样式
        #     'color': None,  # QColor选填，该单元格文字的颜色，例如根据百分比数据大小，大于100%显示红色，小于100%显示绿色
        #     'bg_color': None,  # 选填，该单元格的背景色，例如根据bool数据，True显示绿色，False显示红色
        #     'display': None,  # 选填，该单元显示的内容，例如数据是以分钟为单位，可以在这里给转换成按小时为单位
        #     'align': None,  # 选填，该单元格文字的对齐方式
        #     'font': None,  # 选填，该单元格文字的格式，例如加下划线、加粗等等
        #     'icon': None,  # 选填，该单格元的图标，注意，当 QListView 使用图标模式时，每个item的图片也是在这里设置
        #     'tooltip': None,  # 选填，鼠标指向该单元格时，显示的提示信息
        #     'size': None,  # 选填，该列的 hint size，设置
        #     'data': None,
        #     'edit': None
        # }

    def paintEvent(self, event):
        """Override paintEvent when there is no data to show, draw the preset picture and text."""
        model = utils.real_model(self.model())
        if model is None:
            draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        elif isinstance(model, MTableModel):
            if self.model() is None or self.model().rowCount() == 0:
                draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        return super(MTableView, self).paintEvent(event)

    def save_state(self, name):
        settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "DAYU",
            "dayu_widgets3",
        )
        settings.setValue("{}/headerState".format(name), self.header_view.saveState())

    def load_state(self, name):
        settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "DAYU",
            "dayu_widgets3",
        )
        if settings.value("{}/headerState".format(name)):
            self.header_view.restoreState(settings.value("{}/headerState".format(name)))

    def mouseReleaseEvent(self, event):
        mouse_release_event(self, event)
        return super(MTableView, self).mouseReleaseEvent(event)


class MTreeView(QtWidgets.QTreeView):
    set_header_list = set_header_list
    enable_context_menu = enable_context_menu
    slot_context_menu = slot_context_menu
    sig_context_menu = QtCore.Signal(object)
    slot_left_menu = slot_lift_menu
    sig_left_menu = QtCore.Signal(object)
    sig_link_clicked = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(MTreeView, self).__init__(parent)
        self._no_data_image = None
        self._no_data_text = self.tr("No Data")
        self.header_list = []
        self.header_view = MHeaderView(QtCore.Qt.Horizontal)
        self.setHeader(self.header_view)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)

        self.pressed.connect(self.slot_left_menu)

    def expandAll(self):
        """覆写 expandAll：先一次性加载所有数据，再展开，避免每节点触发 fetchMore 导致大量小插入。

        PySide6/Qt6 的 expandAll 内部实现对每个节点独立调用 fetchMore，而 PySide5/Qt5
        会批量处理。这里先 load_all_data() 将所有数据一次性加载（单个 reset 信号），然后
        批量展开所有节点，PySide2/PySide6 均可获得一致的流畅体验。
        """
        model = utils.real_model(self.model())
        if isinstance(model, MTableModel):
            model.load_all_data()

        self.setUpdatesEnabled(False)
        try:
            super(MTreeView, self).expandAll()
        finally:
            self.setUpdatesEnabled(True)

    def paintEvent(self, event):
        """Override paintEvent when there is no data to show, draw the preset picture and text."""
        model = utils.real_model(self.model())
        if model is None:
            draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        elif isinstance(model, MTableModel):
            if self.model() is None or self.model().rowCount() == 0:
                draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        return super(MTreeView, self).paintEvent(event)

    def set_no_data_text(self, text):
        self._no_data_text = text

    def mouseReleaseEvent(self, event):
        mouse_release_event(self, event)
        return super(MTreeView, self).mouseReleaseEvent(event)


class MBigView(QtWidgets.QListView):
    set_header_list = set_header_list
    enable_context_menu = enable_context_menu
    slot_context_menu = slot_context_menu
    sig_context_menu = QtCore.Signal(object)
    slot_left_menu = slot_lift_menu
    sig_left_menu = QtCore.Signal(object)
    sig_link_clicked = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(MBigView, self).__init__(parent)
        self._no_data_image = None
        self._no_data_text = self.tr("No Data")
        self.header_list = []
        self.header_view = None
        self.setViewMode(QtWidgets.QListView.IconMode)
        try:
            self.setResizeMode(QtWidgets.QListView.Adjust)
        except AttributeError:
            pass  # PySide6: QListView.setResizeMode removed, layout fixed
        self.setMovement(QtWidgets.QListView.Static)
        self.setSpacing(10)
        default_size = dayu_theme.big_view_default_size
        self.setIconSize(QtCore.QSize(default_size, default_size))

        self.pressed.connect(self.slot_left_menu)

    def scale_size(self, factor):
        """Scale the icon size."""
        new_size = self.iconSize() * factor
        max_size = dayu_theme.big_view_max_size
        min_size = dayu_theme.big_view_min_size
        if new_size.width() > max_size:
            new_size = QtCore.QSize(max_size, max_size)
        elif new_size.width() < min_size:
            new_size = QtCore.QSize(min_size, min_size)
        self.setIconSize(new_size)


    def wheelEvent(self, event):
        """Override wheelEvent while user press ctrl, zoom the list view icon size."""
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if hasattr(event, "delta"):
                num_degrees = event.delta() / 8.0
            else:
                # PySide6/PyQt6: QWheelEvent.delta() 已移除，改用 angleDelta
                num_degrees = event.angleDelta().y() / 8.0
            num_steps = num_degrees / 15.0
            factor = pow(1.125, num_steps)
            self.scale_size(factor)
        else:
            super(MBigView, self).wheelEvent(event)

    def paintEvent(self, event):
        """Override paintEvent when there is no data to show, draw the preset picture and text."""
        model = utils.real_model(self.model())
        if model is None:
            draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        elif isinstance(model, MTableModel):
            if self.model() is None or self.model().rowCount() == 0:
                draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        return super(MBigView, self).paintEvent(event)

    def set_no_data_text(self, text):
        self._no_data_text = text

    def mouseReleaseEvent(self, event):
        mouse_release_event(self, event)
        return super(MBigView, self).mouseReleaseEvent(event)


class MListView(QtWidgets.QListView):
    set_header_list = set_header_list
    enable_context_menu = enable_context_menu
    slot_context_menu = slot_context_menu
    sig_context_menu = QtCore.Signal(object)
    slot_left_menu = slot_lift_menu
    sig_left_menu = QtCore.Signal(object)
    sig_link_clicked = QtCore.Signal(object)

    def __init__(self, size=None, parent=None):
        super(MListView, self).__init__(parent)
        self._no_data_image = None
        self._no_data_text = self.tr("No Data")
        self.setProperty("dayu_size", size or dayu_theme.default_size)
        self.header_list = []
        self.header_view = None
        self.setModelColumn(0)
        self.setAlternatingRowColors(True)

        self.pressed.connect(self.slot_left_menu)

    def set_show_column(self, attr):
        for index, attr_dict in enumerate(self.header_list):
            if attr_dict.get("key") == attr:
                self.setModelColumn(index)
                break
        else:
            self.setModelColumn(0)

    def paintEvent(self, event):
        """Override paintEvent when there is no data to show, draw the preset picture and text."""
        model = utils.real_model(self.model())
        if model is None:
            draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        elif isinstance(model, MTableModel):
            if self.model() is None or self.model().rowCount() == 0:
                draw_empty_content(self.viewport(), self._no_data_text, self._no_data_image)
        return super(MListView, self).paintEvent(event)

    def set_no_data_text(self, text):
        self._no_data_text = text

    def mouseReleaseEvent(self, event):
        mouse_release_event(self, event)
        return super(MListView, self).mouseReleaseEvent(event)


if __name__ == "__main__":
    # Import local modules

    from dayu_widgets import dayu_theme
    from dayu_widgets.qt import application

    with application() as app:
        test = MTableView()
        dayu_theme.apply(test)
        test.show()
