#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# 多层级树形数据 + 分页 + 懒加载 测试示例
# 基于 tree_view_multi_level_example.py，增加 MPage 分页能力：
#   - 数据按钮点击加载，自动按当前页大小分页（根节点级分页）
#   - MPage 翻页 / 切换页大小 -> model.set_page 真实切片
#   - 页大小 > lazy_chunk_size(100) 时，页内按 100 条滚动懒加载
#   - 展开节点时子树仍按 lazy_chunk_size 懒加载（与分页正交）
#   - 搜索过滤后重建分页（DataTables 模式：total=匹配数、回第一页）
###################################################################


# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.item_model import MSortFilterModel
from dayu_widgets.item_model import MTableModel
from dayu_widgets.item_view import MTreeView
from dayu_widgets.label import MLabel
from dayu_widgets.line_edit import MLineEdit
from dayu_widgets.page import MPage
from dayu_widgets.push_button import MPushButton

try:
    from examples.tree_view_multi_level_example import generate_deep_tree_data
    from examples.tree_view_multi_level_example import header_list
except ImportError:
    from tree_view_multi_level_example import generate_deep_tree_data
    from tree_view_multi_level_example import header_list


def _count_all_nodes(items):
    """递归统计所有节点数"""
    total = 0
    for item in items:
        total += 1
        children = item.get("children", [])
        if children:
            total += _count_all_nodes(children)
    return total


def _count_large_children(items):
    """统计 children 数量超过 100 的节点数（会被切片）"""
    count = 0
    for item in items:
        children = item.get("children", [])
        if len(children) > 100:
            count += 1
        if children:
            count += _count_large_children(children)
    return count


class TreeViewPagingExample(QtWidgets.QWidget):
    """多层级树形数据 + 分页 + 懒加载 测试窗口"""

    def __init__(self, parent=None):
        super(TreeViewPagingExample, self).__init__(parent)
        self.setWindowTitle("Tree View — Paging + Lazy Loading Test")
        self._source_data = None
        self._init_ui()
        self._load_data(root_count=200, max_l1=20, max_l2=5, max_l3=3)

    def _init_ui(self):
        # ---- Model ----
        self.model_1 = MTableModel(page_size=100)
        self.model_1.set_header_list(header_list)
        self.model_sort = MSortFilterModel()
        self.model_sort.setSourceModel(self.model_1)
        self.model_sort.set_header_list(header_list)
        # 过滤完成后重建分页（DataTables 模式）
        self.model_sort.filter_finished.connect(self._rebuild_after_filter)
        # 整体排序后回到第一页
        self.model_sort.sort_finished.connect(self._on_sort_finished)

        # ---- Tree View ----
        self.tree_view = MTreeView()
        self.tree_view.setModel(self.model_sort)
        self.tree_view.set_header_list(header_list)

        # ---- Info Label ----
        self.info_label = MLabel().secondary()
        self.info_label.setWordWrap(True)

        # ---- MPage (分页) ----
        self.page_set = MPage()
        # 分页粒度选项：>100 的选项用于测试"页内懒加载"（页大小 > lazy_chunk_size）
        self.page_set.set_page_config([25, 50, 100, 200, 500])
        self.page_set.sig_page_changed.connect(self._on_page_changed)

        # ---- Search ----
        self.search_edit = MLineEdit().search().small()
        self.search_edit.setPlaceholderText("Search (triggers full load + rebuild paging)...")
        self.search_edit.textChanged.connect(self.model_sort.set_search_pattern)
        self.clear_search_btn = MPushButton("Clear Search").small()
        self.clear_search_btn.clicked.connect(self.search_edit.clear)

        # ---- Buttons ----
        self.expand_all_btn = MPushButton("Expand All").small()
        self.expand_all_btn.clicked.connect(self.tree_view.expandAll)
        self.collapse_all_btn = MPushButton("Collapse All").small()
        self.collapse_all_btn.clicked.connect(self.tree_view.collapseAll)

        self.load_small_btn = MPushButton("Small (50)").small()
        self.load_small_btn.clicked.connect(lambda: self._load_data(root_count=50, max_l1=8, max_l2=3, max_l3=1))

        self.load_default_btn = MPushButton("Default (200)").small()
        self.load_default_btn.clicked.connect(lambda: self._load_data(root_count=200, max_l1=20, max_l2=5, max_l3=3))

        self.load_large_btn = MPushButton("Large (500)").small()
        self.load_large_btn.clicked.connect(lambda: self._load_data(root_count=500, max_l1=15, max_l2=5, max_l3=3))

        self.load_heavy_btn = MPushButton("Heavy (1000)").small()
        self.load_heavy_btn.clicked.connect(lambda: self._load_data(root_count=1000, max_l1=8, max_l2=3, max_l3=1))

        self.print_stats_btn = MPushButton("Print Stats").small()
        self.print_stats_btn.clicked.connect(self._print_stats)

        # ---- Layout ----
        button_row1 = QtWidgets.QHBoxLayout()
        button_row1.addWidget(MLabel("Data:"))
        button_row1.addWidget(self.load_small_btn)
        button_row1.addWidget(self.load_default_btn)
        button_row1.addWidget(self.load_large_btn)
        button_row1.addWidget(self.load_heavy_btn)
        button_row1.addSpacing(20)
        button_row1.addWidget(self.expand_all_btn)
        button_row1.addWidget(self.collapse_all_btn)
        button_row1.addWidget(self.print_stats_btn)
        button_row1.addStretch()

        button_row2 = QtWidgets.QHBoxLayout()
        button_row2.addWidget(MLabel("Search:"))
        button_row2.addWidget(self.search_edit)
        button_row2.addWidget(self.clear_search_btn)
        button_row2.addStretch()

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.addLayout(button_row1)
        main_lay.addLayout(button_row2)
        main_lay.addWidget(self.info_label)
        main_lay.addWidget(self.tree_view)
        main_lay.addWidget(self.page_set)
        self.setLayout(main_lay)

    def _load_data(self, root_count=200, max_l1=20, max_l2=5, max_l3=3):
        """加载指定规模数据并进入分页模式"""
        data = generate_deep_tree_data(
            root_count=root_count, max_l1=max_l1, max_l2=max_l2, max_l3=max_l3
        )
        self._source_data = data
        self.model_1.set_data_list(data)

        total_nodes = _count_all_nodes(data)
        large_children_count = _count_large_children(data)

        # 根节点级分页：total = 根级数量
        self.page_set.set_total(len(data))
        self.page_set.set_field("current_page", 1)
        self.model_1.page_size = self.page_set.field("page_size_selected")
        self.model_1.set_page(1)

        self.info_label.setText(
            "Root items: {} | Total nodes: {} | Nodes with >100 children: {} | "
            "page_size={} | lazy_chunk_size={} | total_page={}".format(
                len(data),
                total_nodes,
                large_children_count,
                self.model_1.page_size,
                self.model_1.lazy_chunk_size,
                self.page_set.field("total_page"),
            )
        )

    def _on_page_changed(self, page_size, current_page):
        """MPage 翻页 / 切换页大小 -> 真实切片"""
        if page_size != self.model_1.page_size:
            self.model_1.page_size = page_size
        self.model_1.set_page(current_page)

    def _on_sort_finished(self):
        """整体排序后回到第一页，从排序结果的起始看起"""
        self.page_set.set_field("current_page", 1)

    def _rebuild_after_filter(self):
        """过滤完成后重建分页：total=匹配数、回第一页；清空搜索恢复原始数据"""
        if self._source_data is None:
            return
        text = self.search_edit.text()
        if text:
            matched = []
            for row in range(self.model_sort.rowCount()):
                proxy_index = self.model_sort.index(row, 0)
                # 用 mapToSource 取源数据：PySide2 下直接对 proxy index 调 internalPointer 会段错误
                source_index = self.model_sort.mapToSource(proxy_index)
                if source_index.isValid():
                    matched.append(source_index.internalPointer())
            self.model_1.set_data_list(matched, use_slice=True)
            self.page_set.set_total(len(matched))
        else:
            self.model_1.set_data_list(self._source_data, use_slice=True)
            self.page_set.set_total(len(self._source_data))
        self.page_set.set_field("current_page", 1)
        self.model_1.page_size = self.page_set.field("page_size_selected")
        self.model_1.set_page(1)

    def _print_stats(self):
        source = self.model_1
        root_children = source.root_item["children"]
        full_data_map_size = len(source._full_data_map)
        processed_nodes = len(source._processed_nodes)
        total_loaded = len(root_children)
        total_available = len(source.temp_data) if source.temp_data else 0

        print("=" * 60)
        print("Model Stats:")
        print("  Root children loaded: {} / {}".format(total_loaded, total_available))
        print("  Full data map entries: {}".format(full_data_map_size))
        print("  Processed nodes: {}".format(processed_nodes))
        print("  Fully loaded: {}".format(source._data_fully_loaded))
        print("  Page size: {}".format(source.page_size))
        print("  Lazy chunk size: {}".format(source.lazy_chunk_size))
        print("  Paging active: {}".format(source._paging_active))
        print("  Page range: [{}, {})".format(source._page_start, source._page_end))
        print("  MPage total: {} / total_page: {}".format(
            self.page_set.field("total"), self.page_set.field("total_page"))
        )
        print("=" * 60)


if __name__ == "__main__":
    # Import local modules
    from dayu_widgets.qt import application

    with application() as app:
        test = TreeViewPagingExample()
        dayu_theme.apply(test)
        test.resize(1000, 750)
        test.show()
