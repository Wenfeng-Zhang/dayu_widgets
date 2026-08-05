# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets.button_group import MToolButtonGroup
from dayu_widgets.item_model import MSortFilterModel
from dayu_widgets.item_model import MTableModel
from dayu_widgets.item_view import MBigView
from dayu_widgets.item_view import MTableView
from dayu_widgets.line_edit import MLineEdit
from dayu_widgets.page import MPage
from dayu_widgets.tool_button import MToolButton


class MItemViewFullSet(QtWidgets.QWidget):
    sig_double_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_left_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_current_changed = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
    sig_current_row_changed = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
    sig_current_column_changed = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
    sig_selection_changed = QtCore.Signal(QtCore.QItemSelection, QtCore.QItemSelection)
    sig_context_menu = QtCore.Signal(object)
    sig_set_data = QtCore.Signal()

    def __init__(self, table_view=True, big_view=False, parent=None):
        super(MItemViewFullSet, self).__init__(parent)
        self.sort_filter_model = MSortFilterModel()
        self.source_model = MTableModel()
        self.sort_filter_model.setSourceModel(self.source_model)

        self.stack_widget = QtWidgets.QStackedWidget()

        self.view_button_grp = MToolButtonGroup(exclusive=True)
        data_group = []
        if table_view:
            self.table_view = MTableView(show_row_count=True)
            self.table_view.doubleClicked.connect(self.sig_double_clicked)
            self.table_view.pressed.connect(self.slot_left_clicked)
            self.table_view.setModel(self.sort_filter_model)
            self.stack_widget.addWidget(self.table_view)
            data_group.append(
                {"svg": "table_view.svg", "checkable": True, "tooltip": "Table View"}
            )
        if big_view:
            self.big_view = MBigView()
            self.big_view.doubleClicked.connect(self.sig_double_clicked)
            self.big_view.pressed.connect(self.slot_left_clicked)
            self.big_view.setModel(self.sort_filter_model)
            self.stack_widget.addWidget(self.big_view)
            data_group.append(
                {"svg": "big_view.svg", "checkable": True, "tooltip": "Big View"}
            )

        # 设置多个view 共享 MItemSelectionModel
        if self.stack_widget.count() > 0:
            leader_view = self.stack_widget.widget(0)
            self.selection_model = leader_view.selectionModel()
            for index in range(self.stack_widget.count()):
                if index == 0:
                    continue
                other_view = self.stack_widget.widget(index)
                other_view.setSelectionModel(self.selection_model)

            self.selection_model.currentChanged.connect(self.sig_current_changed)
            self.selection_model.currentRowChanged.connect(self.sig_current_row_changed)
            self.selection_model.currentColumnChanged.connect(self.sig_current_column_changed)
            self.selection_model.selectionChanged.connect(self.sig_selection_changed)
        else:
            self.selection_model = None

        self.status_bar = QtWidgets.QLabel()
        self.status_bar.setMaximumWidth(300)
        self.status_bar.setVisible(False)

        self.tool_bar = QtWidgets.QWidget()
        self.top_lay = QtWidgets.QHBoxLayout()
        self.top_lay.setContentsMargins(0, 0, 0, 0)
        self.search_line_edit = MLineEdit().search().small()
        self.search_attr_button = MToolButton().icon_only().svg("down_fill.svg").small()
        self.search_line_edit.set_prefix_widget(self.search_attr_button)
        self.search_line_edit.textChanged.connect(self.sort_filter_model.set_search_pattern)
        self.search_line_edit.setVisible(False)
        self.top_lay.addWidget(self.search_line_edit)

        if data_group and len(data_group) > 1:
            self.view_button_grp.sig_checked_changed.connect(
                self.stack_widget.setCurrentIndex
            )
            self.view_button_grp.set_button_list(data_group)
            self.view_button_grp.set_dayu_checked(0)
            self.top_lay.addWidget(self.view_button_grp)

        self.top_lay.addStretch()
        self.top_lay.addWidget(self.status_bar)
        self.top_lay.addStretch()
        self.tool_bar.setLayout(self.top_lay)

        self.page_set = MPage()
        self.source_model.page_size = self.page_set.field("page_size_selected")
        self.page_set.sig_page_changed.connect(self.slot_page_changed)
        self.sort_filter_model.filter_finished.connect(self.slot_rebuild_after_filter)
        self.sort_filter_model.sort_finished.connect(self.slot_sort_finished)
        self._source_data = None  # setup_data 的原始数据（过滤重建后恢复用）
        self.main_lay = QtWidgets.QVBoxLayout()
        self.main_lay.setSpacing(5)
        self.main_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.addWidget(self.tool_bar)
        self.main_lay.addWidget(self.stack_widget)
        self.main_lay.addWidget(self.page_set)
        self.setLayout(self.main_lay)

    def enable_context_menu(self):
        for index in range(self.stack_widget.count()):
            view = self.stack_widget.widget(index)
            view.enable_context_menu(True)
            view.sig_context_menu.connect(self.sig_context_menu)

    def set_no_data_text(self, text):
        for index in range(self.stack_widget.count()):
            view = self.stack_widget.widget(index)
            view.set_no_data_text(text)

    def set_selection_mode(self, mode):
        for index in range(self.stack_widget.count()):
            view = self.stack_widget.widget(index)
            view.setSelectionMode(mode)

    def enable_status_bar(self):
        self.status_bar.setVisible(True)

    def tool_bar_visible(self, flag):
        self.tool_bar.setVisible(flag)

    @QtCore.Slot(QtCore.QModelIndex)
    def slot_left_clicked(self, start_index):
        button = QtWidgets.QApplication.mouseButtons()
        if button == QtCore.Qt.LeftButton:
            real_index = self.sort_filter_model.mapToSource(start_index)
            self.sig_left_clicked.emit(real_index)

    def set_header_list(self, header_list):
        self.source_model.set_header_list(header_list)
        self.sort_filter_model.set_header_list(header_list)
        self.source_model.clear()
        for index in range(self.stack_widget.count()):
            view = self.stack_widget.widget(index)
            view.set_header_list(header_list)

    def tool_bar_append_widget(self, widget):
        self.top_lay.addWidget(widget)

    def tool_bar_insert_widget(self, widget):
        self.top_lay.insertWidget(0, widget)

    @QtCore.Slot()
    def setup_data(self, data_list):
        self.source_model.clear()
        if data_list:
            self.source_model.set_data_list(data_list)
        # 保存原始数据引用（生成器等一次性迭代器无法恢复，置 None 退化为既有行为）
        self._source_data = data_list if not hasattr(data_list, "__next__") else None
        try:
            total = len(data_list)
        except TypeError:
            # 生成器等无 len() 的可迭代对象（MTableModel 支持 Iterator），总数未知
            total = 0
        self.set_record_count(total)
        # 让表格切片跟随 page_set 当前显示的页码，避免页码与内容不一致
        self.source_model.set_page(self.page_set.field("current_page"))
        self.sig_set_data.emit()

    @QtCore.Slot()
    def slot_rebuild_after_filter(self):
        """过滤完成后重建分页（DataTables 模式）：从过滤结果切片并更新 total。

        搜索时：收集 proxy 的匹配行 -> 重建模型 -> total=匹配数 -> 回第一页；
        清空搜索时：恢复 setup_data 的原始数据。
        生成器等不可恢复的源（_source_data is None）保持既有行为。
        """
        if self._source_data is None:
            return
        text = self.search_line_edit.text()
        if text:
            matched = []
            for row in range(self.sort_filter_model.rowCount()):
                proxy_index = self.sort_filter_model.index(row, 0)
                # 用 mapToSource 取源数据：PySide2 下直接对 proxy index 调 internalPointer 会段错误
                source_index = self.sort_filter_model.mapToSource(proxy_index)
                if source_index.isValid():
                    matched.append(source_index.internalPointer())
            self.source_model.set_data_list(matched, use_slice=True)
            self.set_record_count(len(matched))
        else:
            self.source_model.set_data_list(self._source_data, use_slice=True)
            self.set_record_count(len(self._source_data))
        # 过滤结果变化后从第一页重新展示
        self.page_set.set_field("current_page", 1)
        self.source_model.set_page(1)

    @QtCore.Slot(int)
    def set_record_count(self, total):
        self.page_set.set_total(total)

    @QtCore.Slot(int, int)
    def slot_page_changed(self, page_size, current_page):
        """MPage 翻页时对 MTableModel 做真实切片。"""
        if page_size != self.source_model.page_size:
            self.source_model.page_size = page_size
        self.source_model.set_page(current_page)

    @QtCore.Slot()
    def slot_sort_finished(self):
        """整体排序后回到第一页，从排序结果的起始看起（Web 端标准行为）。"""
        self.page_set.set_field("current_page", 1)

    def get_data(self):
        return self.source_model.get_data_list()

    def searchable(self):
        """Enable search line edit visible."""
        self.search_line_edit.setVisible(True)
        return self

    def set_status_bar(self, text):
        self.status_bar.setText(text)


if __name__ == '__main__':
    from dayu_widgets.qt import application
    from dayu_widgets import dayu_theme
    from statics.ui_config import resource_manager_config

    with application() as app:
        # test = MItemViewFullSet(table_view=False, big_view=True)
        test = MItemViewFullSet(table_view=True, big_view=False)
        # test.show_row_count(False)
        dayu_theme.apply(test)
        # header_list = resource_manager_config.CONFIG_DICT.get('tab_list')[0].get('header_list')
        # print(header_list)
        # test.set_header_list(header_list)
        # test.set_header_list([{'label': 'Name', 'key': 'name', 'icon': lambda x, y: y['icon']}])
        test.set_header_list([
            {'label': 'Name', 'key': 'name', "searchable": True, 'icon': lambda x, y: y['icon']},
            {'label': 'test', 'key': 'test', "searchable": True, 'icon': lambda x, y: y['icon']}
        ])

        test.setup_data([{'url': '/launch/launcher_a0003/nuke', 'name': u'nuke 12.2v5 \u901a\u7528', 'icon': 'app-nuke.png'}, {'url': '/launch/launcher_a0003/clarisse', 'name': u'clarisse 4.0 SP14 \u901a\u7528', 'icon': 'app-clarisse.png'}, {'url': '/launch/launcher_a0003/maya', 'name': u'maya 2018 ar 5.2.2.1', 'icon': 'app-maya.png'}])
        test.page_set.setVisible(False)
        test.searchable()
        test.show()






