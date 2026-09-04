#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# 极限压力测试示例：父集 50000 个根节点，每个根节点只有 1 个子节点
# 用于测试 MTableModel 在 5 万规模下的：
#   - 懒加载（lazy_chunk_size=100 滚动块）
#   - 分页 + 页内懒加载（MPage，页大小 >100 时页内滚动补）
#   - 整体排序（C 级 sorted，5 万行耗时）
#   - 搜索过滤 + 重建分页（DataTables 模式）
#   - 展开节点（每个根只有 1 个子节点）
###################################################################


import random
import time

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

SEX_OPTIONS = ["Male", "Female"]
CITY_OPTIONS = [
    "New York", "London", "Sydney", "Ottawa",
    "Beijing", "Shanghai", "Shenzhen", "Guangzhou",
    "Tokyo", "Seoul", "Paris", "Berlin",
]

header_list = [
    {"label": "Name", "key": "name", "checkable": True, "searchable": True, "width": 220, "icon": "user_fill.svg"},
    {"label": "Sex", "key": "sex", "searchable": True},
    {"label": "Age", "key": "age", "width": 80, "searchable": True, "display": lambda x, y: "{} 岁".format(x)},
    {"label": "City", "key": "city", "searchable": True, "width": 120},
    {"label": "Score", "key": "score", "searchable": True, "width": 80},
    {"label": "Level", "key": "level", "width": 60, "display": lambda x, y: "L{}".format(x)},
]


def _make_row(name, level):
    """生成单行数据"""
    return {
        "name": name,
        "sex": random.choice(SEX_OPTIONS),
        "age": random.randint(18, 60),
        "city": random.choice(CITY_OPTIONS),
        "score": random.randint(0, 100),
        "level": level,
    }


def generate_flat_tree_data(root_count=50000):
    """生成极限测试数据：root_count 个根节点，每个恰好 1 个子节点。"""
    random.seed(42)
    data = []
    for i in range(root_count):
        root_name = "Root_%05d" % i
        root_row = _make_row(root_name, 0)
        # 每个根节点恰好 1 个子节点
        root_row["children"] = [_make_row("{} > Child_0".format(root_name), 1)]
        data.append(root_row)
    return data


class TreeView50000Example(QtWidgets.QWidget):
    """50000 根节点极限测试窗口"""

    def __init__(self, parent=None):
        super(TreeView50000Example, self).__init__(parent)
        self.setWindowTitle("Tree View — 50000 Roots Stress Test")
        self._source_data = None
        self._gen_time = 0.0
        self._paging_enabled = False  # 默认不分页，点击 Enable Paging 后进入分页模式
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        # ---- Model ----
        self.model_1 = MTableModel(page_size=100)
        self.model_1.set_header_list(header_list)
        self.model_sort = MSortFilterModel()
        self.model_sort.setSourceModel(self.model_1)
        self.model_sort.set_header_list(header_list)
        self.model_sort.filter_finished.connect(self._rebuild_after_filter)
        self.model_sort.sort_finished.connect(self._on_sort_finished)

        # ---- Tree View ----
        self.tree_view = MTreeView()
        self.tree_view.setModel(self.model_sort)
        self.tree_view.set_header_list(header_list)

        # ---- Info Label ----
        self.info_label = MLabel().secondary()
        self.info_label.setWordWrap(True)

        # ---- MPage（默认隐藏，点击 Enable Paging 后显示）----
        self.page_set = MPage()
        self.page_set.set_page_config([25, 50, 100, 200, 500])
        self.page_set.sig_page_changed.connect(self._on_page_changed)
        self.page_set.setVisible(False)

        # ---- Paging Toggle ----
        self.paging_btn = MPushButton("Enable Paging").small()
        self.paging_btn.setCheckable(True)
        self.paging_btn.toggled.connect(self._toggle_paging)

        # ---- Search ----
        self.search_edit = MLineEdit().search().small()
        self.search_edit.setPlaceholderText("Search (full scan + rebuild paging)...")
        self.search_edit.textChanged.connect(self.model_sort.set_search_pattern)
        self.clear_search_btn = MPushButton("Clear Search").small()
        self.clear_search_btn.clicked.connect(self.search_edit.clear)

        # ---- Buttons ----
        self.expand_all_btn = MPushButton("Expand First 50 Roots").small()
        self.expand_all_btn.clicked.connect(self._expand_first_50)
        self.collapse_all_btn = MPushButton("Collapse All").small()
        self.collapse_all_btn.clicked.connect(self.tree_view.collapseAll)

        self.reload_btn = MPushButton("Reload 50000").small()
        self.reload_btn.clicked.connect(self._load_data)

        self.print_stats_btn = MPushButton("Print Stats").small()
        self.print_stats_btn.clicked.connect(self._print_stats)

        # ---- Layout ----
        button_row1 = QtWidgets.QHBoxLayout()
        button_row1.addWidget(MLabel("Stress:"))
        button_row1.addWidget(self.reload_btn)
        button_row1.addWidget(self.paging_btn)
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

    def _load_data(self):
        """生成 50000 根节点并加载（默认纯懒加载，不分页）"""
        t0 = time.perf_counter()
        data = generate_flat_tree_data(root_count=50000)
        self._gen_time = time.perf_counter() - t0

        t1 = time.perf_counter()
        self._source_data = data
        self.model_1.set_data_list(data)  # 纯懒加载：children = 前 lazy_chunk_size 条
        load_time = time.perf_counter() - t1

        total_nodes = len(data) * 2  # 每根 1 子
        self.info_label.setText(
            "Root: 50000 | Total nodes: {} | 每个根 1 个子节点\n"
            "生成耗时: {:.2f}s | 加载耗时: {:.2f}s | 当前: 懒加载模式（lazy_chunk_size={}）".format(
                total_nodes, self._gen_time, load_time, self.model_1.lazy_chunk_size
            )
        )
        if self._paging_enabled:
            # 重新加载后若分页已启用，恢复分页显示
            self._enter_paging()

    def _enter_paging(self):
        """进入分页模式：显示 MPage 并按当前页大小切片"""
        self.model_1.page_size = self.page_set.field("page_size_selected")
        self.page_set.set_total(len(self._source_data) if self._source_data else 0)
        self.page_set.set_field("current_page", 1)
        self.model_1.set_page(1)

    def _exit_paging(self):
        """退出分页模式：隐藏 MPage 并恢复纯懒加载"""
        self.model_1.set_data_list(self._source_data, use_slice=True)
        self.page_set.setVisible(False)

    def _toggle_paging(self, checked):
        """Enable/Disable Paging 开关"""
        self._paging_enabled = checked
        self.paging_btn.setText("Disable Paging" if checked else "Enable Paging")
        if checked:
            self.page_set.setVisible(True)
            self._enter_paging()
        else:
            self._exit_paging()

    def _on_page_changed(self, page_size, current_page):
        if not self._paging_enabled:
            return
        if page_size != self.model_1.page_size:
            self.model_1.page_size = page_size
        self.model_1.set_page(current_page)

    def _on_sort_finished(self):
        if self._paging_enabled:
            self.page_set.set_field("current_page", 1)

    def _rebuild_after_filter(self):
        """过滤完成重建（DataTables 模式）：分页启用时重建分页，否则保持懒加载"""
        if self._source_data is None:
            return
        text = self.search_edit.text()
        t0 = time.perf_counter()
        if text:
            matched = []
            for row in range(self.model_sort.rowCount()):
                proxy_index = self.model_sort.index(row, 0)
                source_index = self.model_sort.mapToSource(proxy_index)
                if source_index.isValid():
                    matched.append(source_index.internalPointer())
            self.model_1.set_data_list(matched, use_slice=True)
        else:
            self.model_1.set_data_list(self._source_data, use_slice=True)
        if self._paging_enabled:
            total = len(self.model_1.temp_data) if self.model_1.temp_data else 0
            self.page_set.set_total(total)
            self.page_set.set_field("current_page", 1)
            self.model_1.page_size = self.page_set.field("page_size_selected")
            self.model_1.set_page(1)
        elapsed = time.perf_counter() - t0
        mode = "分页" if self._paging_enabled else "懒加载"
        self.info_label.setText(
            "{} 重建耗时: {:.2f}s | 模式: {} | total={} | total_page={}".format(
                "过滤" if text else "恢复", elapsed, mode, self.page_set.field("total"),
                self.page_set.field("total_page") if self._paging_enabled else "-",
            )
        )

    def _expand_first_50(self):
        """展开前 50 个根节点，观察子树懒加载"""
        for row in range(min(50, self.model_sort.rowCount())):
            self.tree_view.expand(self.model_sort.index(row, 0))
        self.tree_view.viewport().update()

    def _print_stats(self):
        source = self.model_1
        root_children = source.root_item["children"]
        t0 = time.perf_counter()

        print("=" * 60)
        print("Model Stats:")
        print("  Root children loaded: {} / {}".format(len(root_children), len(source.temp_data) if source.temp_data else 0))
        print("  Full data map entries: {}".format(len(source._full_data_map)))
        print("  Processed nodes: {}".format(len(source._processed_nodes)))
        print("  Fully loaded: {}".format(source._data_fully_loaded))
        print("  Page size: {} | Lazy chunk: {} | Paging active: {}".format(
            source.page_size, source.lazy_chunk_size, source._paging_active))
        print("  Page range: [{}, {})".format(source._page_start, source._page_end))
        print("  MPage total: {} / total_page: {}".format(
            self.page_set.field("total"), self.page_set.field("total_page")))
        print("  Data gen time: {:.2f}s".format(self._gen_time))
        print("=" * 60)


if __name__ == "__main__":
    # Import local modules
    from dayu_widgets.qt import application

    with application() as app:
        test = TreeView50000Example()
        dayu_theme.apply(test)
        test.resize(1100, 800)
        test.show()
