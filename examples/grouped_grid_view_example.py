#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Grouped Grid View 示例
#
# 演示 MGroupedGridView：
#   - 顶部工具栏：表格/大图切换、分组依据菜单、展开/折叠、搜索
#   - 按 header_list 中的字段多选分组（可选 sex / age / city）
#   - 分组表格：MTreeView + 组头自绘（灰底 + 彩色左边条 + 三角箭头）
#   - 分组大图：GroupedBigView，按组分块的缩略图流（只显示有 image 的行）
###################################################################

# Import third-party modules
from Qt import QtWidgets

# Import local modules
from dayu_widgets import MGroupedGridView
from dayu_widgets import dayu_theme
try:
    import examples._mock_data as mock
except ImportError:
    import _mock_data as mock


def with_images(rows):
    """给部分数据行补一个 icon 作为缩略图（大图模式只显示有 image 的行）。"""
    result = []
    for i, row in enumerate(list(rows)):
        d = dict(row)
        if i % 3 != 0:
            d["image"] = "user_fill.svg"
        result.append(d)
    return result


class GroupedGridViewExample(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(GroupedGridViewExample, self).__init__(parent)
        self.setWindowTitle("Grouped Grid View Example")

        self.grouped_view = MGroupedGridView()
        self.grouped_view.set_header_list(mock.header_list)
        self.grouped_view.set_group_fields(["sex", "city"])
        self.grouped_view.setup_data(with_images(mock.data_list))
        self.grouped_view.sig_double_clicked.connect(self._on_double_clicked)

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(self.grouped_view)
        self.setLayout(main_lay)

    def _on_double_clicked(self, index):
        data = index.internalPointer()
        print("double clicked:", data.get("name") if isinstance(data, dict) else data)


if __name__ == "__main__":
    # Import local modules
    from dayu_widgets.qt import application

    with application() as app:
        test = GroupedGridViewExample()
        dayu_theme.apply(test)
        test.resize(1000, 750)
        test.show()
