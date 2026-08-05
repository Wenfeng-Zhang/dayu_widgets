#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: Mu yanru
# Date  : 2019.2
# Email : muyanru345@163.com
###################################################################

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random

# Import third-party modules
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.field_mixin import MFieldMixin
from dayu_widgets.item_model import MSortFilterModel
from dayu_widgets.item_model import MTableModel
from dayu_widgets.item_view import MTreeView
from dayu_widgets.line_edit import MLineEdit
from dayu_widgets.push_button import MPushButton
try:
    import examples._mock_data as mock
except ImportError:
    import _mock_data as mock


class TreeViewExample(QtWidgets.QWidget, MFieldMixin):
    def __init__(self, parent=None):
        super(TreeViewExample, self).__init__(parent)
        self.setWindowTitle("TreeView Example")
        self._init_ui()

    def _init_ui(self):
        model_1 = MTableModel()
        self.model_1 = model_1
        model_1.set_header_list(mock.header_list)
        model_sort = MSortFilterModel()
        model_sort.setSourceModel(model_1)

        tree_view = MTreeView()
        tree_view.setModel(model_sort)

        model_sort.set_header_list(mock.header_list)
        tree_view.set_header_list(mock.header_list)
        model_1.set_data_list(mock.tree_data_list)
        # model_1.checkStateChanged.connect(self.print_)
        model_1.dataChanged.connect(self.print_)

        line_edit = MLineEdit().search().small()
        line_edit.textChanged.connect(model_sort.set_search_pattern)

        expand_all_button = MPushButton("Expand All").small()
        expand_all_button.clicked.connect(tree_view.expandAll)
        collapse_all_button = MPushButton("Collapse All").small()
        collapse_all_button.clicked.connect(tree_view.collapseAll)
        button_lay = QtWidgets.QHBoxLayout()
        button_lay.addWidget(expand_all_button)
        button_lay.addWidget(collapse_all_button)
        button_lay.addWidget(line_edit)
        button_lay.addStretch()

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.addLayout(button_lay)
        main_lay.addWidget(tree_view)
        main_lay.addStretch()
        self.setLayout(main_lay)

    def print_(self, *args, **kwargs):
        model = args[0]
        plugin = model.internalPointer()
        if plugin is not None:
            print(plugin.get('name'))
        # print(kwargs)


def generate_tree_data_list(num_rows=300, num_children=5):
    # Define a function to generate a single row of data
    def generate_row(name_suffix):
        return {
            "name": f"Name {name_suffix}",
            "sex": random.choice(["Male", "Female"]),
            "age": random.randint(18, 60),
            "score": random.randint(50, 100),
            "city": random.choice(["New York", "London", "Sydney", "Ottawa"]),
            "date": f"2016-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        }

    # Generate the main list of rows, each with children
    data_list = []
    for i in range(num_rows):
        parent_row = generate_row(i)
        # parent_row["children"] = [generate_row(f"{i}-{j}") for j in range(num_children)]
        data_list.append(parent_row)

    return data_list



if __name__ == "__main__":
    # Import local modules
    from dayu_widgets import dayu_theme
    from dayu_widgets.qt import application

    with application() as app:
        test = TreeViewExample()
        dayu_theme.apply(test)
        test.model_1.set_data_list(generate_tree_data_list())
        test.show()
