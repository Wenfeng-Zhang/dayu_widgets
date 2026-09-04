#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# 多层级树形数据测试示例
# 用于测试 MTableModel 的延迟加载/缓存机制
# 包含 4 层深度、超过 page_size(100) 的子节点，触发懒加载分页
###################################################################


import random

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
from dayu_widgets.push_button import MPushButton

SEX_OPTIONS = ["Male", "Female"]
CITY_OPTIONS = [
    "New York", "London", "Sydney", "Ottawa",
    "Beijing", "Shanghai", "Shenzhen", "Guangzhou",
    "Tokyo", "Seoul", "Paris", "Berlin",
]

header_list = [
    {
        "label": "Name",
        "key": "name",
        "checkable": True,
        "searchable": True,
        "width": 220,
        "icon": "user_fill.svg",
    },
    {
        "label": "Sex",
        "key": "sex",
        "searchable": True,
        "icon": lambda x, y: (
            "{}.svg".format(x.lower()) if x else "user_fill.svg",
            getattr(dayu_theme, "{}_color".format(x.lower())) if x else None,
        ),
    },
    {
        "label": "Age",
        "key": "age",
        "width": 80,
        "searchable": True,
        "display": lambda x, y: "{} 岁".format(x),
    },
    {
        "label": "City",
        "key": "city",
        "searchable": True,
        "width": 120,
    },
    {
        "label": "Score",
        "key": "score",
        "searchable": True,
        "width": 80,
    },
    {
        "label": "Level",
        "key": "level",
        "width": 60,
        "display": lambda x, y: "L{}".format(x),
    },
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


def generate_deep_tree_data(root_count=200, max_l1=20, max_l2=5, max_l3=3):
    """
    生成多层级树形数据，用于测试延迟加载机制

    层级结构:
        L0 (根节点子项): root_count 个, 每个有 0~max_l1 个子项
        L1: 0~max_l1 个, 每个有 0~max_l2 个子项
        L2: 0~max_l2 个, 每个有 0~max_l3 个子项
        L3: 0~max_l3 个 (叶节点)

    关键测试点:
        - root_count > page_size(100): 触发根级别懒加载，只展示前 100 条
        - 子节点较少，保证首次加载和搜索速度
        - Large/Huge 预设提供不同规模用于性能对比
    """
    random.seed(42)  # 固定种子，方便复现

    def _build_children(parent_name, level, count_range, max_depth):
        if level >= max_depth:
            return None
        child_count = random.randint(0, count_range)
        if child_count == 0:
            return []
        children = []
        for i in range(child_count):
            child_name = "{} > Child_{}".format(parent_name, i)
            child = _make_row(child_name, level)
            if level + 1 < max_depth:
                next_range = [max_l1, max_l2, max_l3][min(level, 2)]
                sub_children = _build_children(child_name, level + 1, next_range, max_depth)
                if sub_children is not None:
                    child["children"] = sub_children
            children.append(child)
        return children

    data_list = []
    for i in range(root_count):
        parent_name = "Root_{:03d}".format(i)
        root_row = _make_row(parent_name, 0)
        sub_children = _build_children(parent_name, 1, max_l1, 4)
        if sub_children is not None:
            root_row["children"] = sub_children
        data_list.append(root_row)

    # 统计总节点数
    def _count_nodes(items):
        total = 0
        for item in items:
            total += 1
            children = item.get("children", [])
            if children:
                total += _count_nodes(children)
        return total

    total = _count_nodes(data_list)
    print("Generated tree: {} root items, {} total nodes".format(root_count, total))
    return data_list


class TreeViewMultiLevelExample(QtWidgets.QWidget):
    """多层级树形数据测试窗口"""

    def __init__(self, parent=None):
        super(TreeViewMultiLevelExample, self).__init__(parent)
        self.setWindowTitle("Multi-Level Tree View — Lazy Loading Test")
        self._init_ui()
        self._load_default_data()

    def _init_ui(self):
        # ---- Model ----
        self.model_1 = MTableModel(page_size=100)
        self.model_1.set_header_list(header_list)
        self.model_sort = MSortFilterModel()
        self.model_sort.setSourceModel(self.model_1)
        self.model_sort.set_header_list(header_list)

        # ---- Tree View ----
        self.tree_view = MTreeView()
        self.tree_view.setModel(self.model_sort)
        self.tree_view.set_header_list(header_list)

        # ---- Info Label ----
        self.info_label = MLabel().secondary()
        self.info_label.setWordWrap(True)

        # ---- Search ----
        self.search_edit = MLineEdit().search().small()
        self.search_edit.setPlaceholderText("Search (triggers full data load)...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.clear_search_btn = MPushButton("Clear Search").small()
        self.clear_search_btn.clicked.connect(self._on_clear_search)

        # ---- Buttons ----
        self.expand_all_btn = MPushButton("Expand All").small()
        self.expand_all_btn.clicked.connect(self.tree_view.expandAll)
        self.collapse_all_btn = MPushButton("Collapse All").small()
        self.collapse_all_btn.clicked.connect(self.tree_view.collapseAll)

        self.load_small_btn = MPushButton("Small (50)").small()
        self.load_small_btn.clicked.connect(lambda: self._load_data(root_count=50, max_l1=8, max_l2=3, max_l3=1))

        self.load_default_btn = MPushButton("Default (200)").small()
        self.load_default_btn.clicked.connect(self._load_default_data)

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
        self.setLayout(main_lay)

    def _load_data(self, root_count=200, max_l1=20, max_l2=5, max_l3=3):
        """加载指定规模的测试数据"""
        data = generate_deep_tree_data(
            root_count=root_count, max_l1=max_l1, max_l2=max_l2, max_l3=max_l3
        )
        # 统计信息
        total_nodes = _count_all_nodes(data)
        large_children_count = _count_large_children(data)

        self.model_1.set_data_list(data)
        self.info_label.setText(
            "Root items: {} | Total nodes: {} | Nodes with >100 children: {} | "
            "page_size={}".format(
                root_count, total_nodes, large_children_count, self.model_1.page_size
            )
        )

    def _load_default_data(self):
        self._load_data(root_count=200, max_l1=20, max_l2=5, max_l3=3)

    def _on_search_changed(self, text):
        self.model_sort.set_search_pattern(text)

    def _on_clear_search(self):
        self.search_edit.clear()

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
        print("  Delayed loading: {}".format(source.use_delayed_loading))
        print("=" * 60)


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


if __name__ == "__main__":
    # Import local modules
    from dayu_widgets.qt import application

    with application() as app:
        test = TreeViewMultiLevelExample()
        dayu_theme.apply(test)
        test.resize(1000, 700)
        test.show()
