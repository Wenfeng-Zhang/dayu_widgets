# -*- coding: utf-8 -*-
"""分组表格 / 分组大图控件。

- 复用 dayu 原生 MTreeView + MTableModel + MSortFilterModel，缩略图/状态色/字体
  与原表格完全一致；
- MTableModel 原生支持树形（"children" 键），把扁平数据按选定字段逐层嵌套即可
  （见 group_builder.py），天然支持多字段分组；
- 顶部提供【多选】分组字段按钮，按勾选顺序逐层分组；
- 保留原表格的「视图切换」：
    · 分组表格：MTreeView，灰色组头 + 自绘三角箭头；
    · 分组大图：GroupedBigView，按组分块的缩略图流。

用法：
    view = MGroupedGridView()
    view.set_header_list(header_list)   # 与 grid_view 完全相同
    view.set_group_fields(["season"])   # 可选：默认分组字段(有序)
    view.setup_data(data_list)          # 扁平 [row_dict, ...]
"""
# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.button_group import MToolButtonGroup
from dayu_widgets.group_builder import GROUP_LEVEL_KEY
from dayu_widgets.group_builder import GROUP_TEXT_KEY
from dayu_widgets.group_builder import build_grouped_tree
from dayu_widgets.group_builder import is_group_row
from dayu_widgets.grouped_big_view import GroupedBigView
from dayu_widgets.item_model import MSortFilterModel
from dayu_widgets.item_model import MTableModel
from dayu_widgets.item_view import MTreeView
from dayu_widgets.label import MLabel
from dayu_widgets.line_edit import MLineEdit
from dayu_widgets.menu import MMenu
from dayu_widgets.push_button import MPushButton
from dayu_widgets.qt import get_scale_factor


# 组头行配色：靠"阶梯背景 + 左侧暗色沟槽 + 彩色左边条"三招拉开层级
_GROUP_GUTTER = QtGui.QColor("#242424")    # 左侧沟槽(比所有层都暗)，让子组明显内缩
_GROUP_BG = ["#3d4653", "#474747", "#565656", "#646464", "#727272"]  # 各层背景(逐层变亮)
_GROUP_ACCENT = ["#4a90d9", "#57a86b", "#d0a13a", "#b06bd0", "#d06b6b"]  # 各层左边条彩色
_GROUP_FG = QtGui.QColor("#ffffff")
_ARROW_COLOR = QtGui.QColor("#f0f0f0")
_GROUP_SEP = QtGui.QColor("#2a2a2a")       # 组头底部分隔线
_GROUP_INDENT_STEP = 10             # 每层缩进（多级分组时每往下一层的左缩进量）
_GROUP_BAR_W = 3                     # 彩色左边条宽度
# 组头行高：约为表头/数据行(=dayu_theme.default_size)的 85%，比表头略矮但不局促
_GROUP_ROW_H = max(int(dayu_theme.default_size * 0.85), 28)


def _level_color(palette, level):
    return QtGui.QColor(palette[min(max(level, 0), len(palette) - 1)])


def _source_obj(index):
    """从(可能是 proxy 的) index 取底层 data_dict。"""
    model = index.model()
    if model is None:
        return None
    if hasattr(model, "mapToSource"):
        return model.mapToSource(index).internalPointer()
    return index.internalPointer()


class _GroupRowDelegate(QtWidgets.QStyledItemDelegate):
    """组头行自绘：整行灰底 + 彩色左边条 + 白字组名 + 三角箭头。

    - 数据行：交回 super().paint()，缩略图/状态色/字体全部保持原表格效果；
    - 组头行：已 setFirstColumnSpanned 跨满整行，故只在第 0 列绘制整行内容
      （暗色沟槽 + 阶梯背景 + 彩色左边条 + 三角箭头 + 组名）。
    """

    def __init__(self, tree_view, get_group_label):
        super(_GroupRowDelegate, self).__init__(tree_view)
        self._tree_view = tree_view
        self._get_group_label = get_group_label

    def sizeHint(self, option, index):
        # 数据行恢复成原表格行高(dayu_theme.default_size≈48)；组头行更矮，
        # 让分组读起来像"小分隔条"，比表头/数据行都小，不抢视觉。
        # 组头节点不调 super().sizeHint()：组头 dict 没有 header 字段，
        # 默认 sizeHint 会访问 model.data() 触发 formatter 对 None 处理，PySide6 下易段错误。
        if is_group_row(_source_obj(index)):
            hint = QtCore.QSize(option.rect.width(), _GROUP_ROW_H)
            return hint
        hint = super(_GroupRowDelegate, self).sizeHint(option, index)
        hint.setHeight(dayu_theme.default_size)
        return hint

    def _visible_leaf_count(self, proxy_index):
        """统计该组下当前可见（经搜索过滤后）的叶子行数，供组头动态显示计数。"""
        model = self._tree_view.model()
        total = 0
        for r in range(model.rowCount(proxy_index)):
            child = model.index(r, 0, proxy_index)
            if is_group_row(_source_obj(child)):
                total += self._visible_leaf_count(child)
            else:
                total += 1
        return total

    def paint(self, painter, option, index):
        data_obj = _source_obj(index)
        if not is_group_row(data_obj):
            super(_GroupRowDelegate, self).paint(painter, option, index)
            return

        # 组头行的「整行」只由第 0 列绘制（背景+左条+箭头+组名，rect 扩展到整行宽度），
        # 其它列（含 selectable/editable 列的 delegate）必须直接 return、什么都不画，
        # 否则会覆盖整行背景并重新画出下层数据的人像图标/配色，把分组栏切成一块块。
        if index.column() != 0:
            return

        painter.save()
        level = data_obj.get(GROUP_LEVEL_KEY, 0)
        rect = QtCore.QRect(option.rect)
        # 扩展到整行宽度（不依赖 setFirstColumnSpanned：该 API 在 PySide6 下会段错误）
        viewport_width = self._tree_view.viewport().width()
        if rect.right() < viewport_width:
            rect.setRight(viewport_width)
        bar_x = rect.left() + level * _GROUP_INDENT_STEP

        # ① 整行先铺暗色沟槽 → ② 从缩进处起铺该层背景（逐层变亮）
        painter.fillRect(rect, _GROUP_GUTTER)
        area = QtCore.QRect(rect)
        area.setLeft(bar_x)
        painter.fillRect(area, _level_color(_GROUP_BG, level))
        # ③ 缩进处画一条彩色左边条，颜色随层级变化
        painter.fillRect(QtCore.QRect(bar_x, rect.top(), _GROUP_BAR_W, rect.height()),
                         _level_color(_GROUP_ACCENT, level))

        # 底部分隔线
        painter.setPen(_GROUP_SEP)
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # 箭头 + 组名
        expanded = self._tree_view.isExpanded(index)
        cx = bar_x + _GROUP_BAR_W + 12
        cy = rect.center().y()
        s = 6
        # 注意：不要在 item delegate 里 setRenderHint(Antialiasing)，PySide6 下会段错误
        painter.setBrush(_ARROW_COLOR)
        painter.setPen(QtCore.Qt.NoPen)
        if expanded:
            path = QtGui.QPainterPath()
            path.moveTo(cx - s, cy - s + 2)
            path.lineTo(cx + s, cy - s + 2)
            path.lineTo(cx, cy + s)
            path.closeSubpath()
        else:
            path = QtGui.QPainterPath()
            path.moveTo(cx - s + 2, cy - s)
            path.lineTo(cx - s + 2, cy + s)
            path.lineTo(cx + s + 2, cy)
            path.closeSubpath()
        painter.drawPath(path)

        base = self._get_group_label(data_obj) or ""
        text = u"{}  ({})".format(base, self._visible_leaf_count(index))
        painter.setPen(_GROUP_FG)
        font = QtGui.QFont(option.font)
        font.setBold(True)
        ps = font.pointSize()
        if ps > 0:
            font.setPointSize(max(ps - 1, 1))
        painter.setFont(font)
        text_rect = QtCore.QRect(rect)
        text_rect.setLeft(cx + s + 10)
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)
        painter.restore()


class MGroupedGridView(QtWidgets.QWidget):
    sig_double_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_left_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_link_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_current_changed = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
    sig_current_row_changed = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
    sig_current_column_changed = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
    sig_selection_changed = QtCore.Signal(object, object)
    sig_context_menu = QtCore.Signal(object)
    sig_refresh = QtCore.Signal()

    def __init__(self, parent=None):
        self._group_fields = []
        self._all_data = []
        self._expanded = True
        self._grouped_roots = []
        super(MGroupedGridView, self).__init__(parent)
        self.init_widget()

    def init_widget(self):
        scale_x, _ = get_scale_factor()

        self.source_model = MTableModel()
        self.sort_filter_model = MSortFilterModel()
        self.sort_filter_model.setSourceModel(self.source_model)

        # --- 视图一：分组表格（原 Table View）---
        self.tree_view = MTreeView()
        self.tree_view.setModel(self.sort_filter_model)
        self.tree_view.setItemDelegate(
            _GroupRowDelegate(self.tree_view, self._group_label_of))
        # 关掉原生分支箭头，组头由 delegate 自绘三角（组头行会 setFirstColumnSpanned 跨整行）
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setIndentation(0)
        # 关掉交替行底色：搜索过滤后重绘时，交替底色会在组头行露出"条纹"
        self.tree_view.setAlternatingRowColors(False)
        # 表头各列之间加竖直分界线
        self.tree_view.header().setStyleSheet(
            "QHeaderView::section { border-right: 1px solid #2a2a2a; }")
        # 最后一列撑满剩余宽度，避免列宽之和小于视口时右侧出现大片空白，
        # 导致分组行在视觉上被「切断」成几块。
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.doubleClicked.connect(self.slot_double_clicked)
        self.tree_view.pressed.connect(self.slot_left_clicked)
        self.tree_view.enable_context_menu(True)
        self.tree_view.sig_context_menu.connect(self.sig_context_menu)

        # --- 视图二：分组大图（原 Big View）---
        self.big_view = GroupedBigView()
        self.big_view.set_icon_size(
            QtCore.QSize(dayu_theme.big_view_default_size, dayu_theme.big_view_default_size))
        self.big_view.sig_double_clicked.connect(self.sig_double_clicked)
        self.big_view.sig_left_clicked.connect(self.sig_left_clicked)
        self.big_view.sig_context_menu.connect(self.sig_context_menu)

        self.stack_widget = QtWidgets.QStackedWidget()
        self.stack_widget.addWidget(self.tree_view)
        self.stack_widget.addWidget(self.big_view)

        # --- 视图切换按钮 ---
        data_group = [
            {"svg": "table_view.svg", "checkable": True, "tooltip": "分组表格"},
            {"svg": "big_view.svg", "checkable": True, "tooltip": "分组大图"},
        ]
        self.view_button_grp = MToolButtonGroup(exclusive=True)
        self.view_button_grp.set_button_list(data_group)
        self.view_button_grp.sig_checked_changed.connect(
            self.stack_widget.setCurrentIndex)
        self.view_button_grp.set_dayu_checked(0)

        # --- 分组控件 ---
        self.group_button = MPushButton(text="分组：无").small()
        self.group_button.setMinimumWidth(160 * scale_x)
        self.group_button.clicked.connect(self._show_group_menu)

        self.expand_button = MPushButton(text="展开/折叠").small()
        self.expand_button.clicked.connect(self._toggle_expand)

        self.search_line_edit = MLineEdit().search().small()
        self.search_line_edit.setMaximumWidth(200 * scale_x)
        self.search_line_edit.setPlaceholderText("搜索...")
        self.search_line_edit.textChanged.connect(self._on_search)

        tool_lay = QtWidgets.QHBoxLayout()
        tool_lay.setContentsMargins(0, 0, 0, 0)
        tool_lay.setSpacing(6)
        tool_lay.addWidget(self.view_button_grp)
        tool_lay.addWidget(MLabel("分组依据"))
        tool_lay.addWidget(self.group_button)
        tool_lay.addWidget(self.expand_button)
        tool_lay.addStretch()
        tool_lay.addWidget(self.search_line_edit)
        self.tool_bar = QtWidgets.QWidget()
        self.tool_bar.setLayout(tool_lay)

        self.page_info_label = MLabel().secondary()
        self.page_info_label.setAlignment(QtCore.Qt.AlignCenter)

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.setSpacing(5)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(self.tool_bar)
        main_lay.addWidget(self.stack_widget)
        main_lay.addWidget(self.page_info_label)
        self.setLayout(main_lay)

        self.set_header_list([])

    # ---------- 对外接口 ----------
    def set_header_list(self, header_list):
        self.header_list = header_list or []
        self.source_model.set_header_list(self.header_list)
        self.sort_filter_model.set_header_list(self.header_list)
        self.tree_view.set_header_list(self.header_list)
        self.big_view.set_header_list(self.header_list)
        self._update_group_button_text()

    def setup_data(self, data_list):
        self._all_data = list(data_list or [])
        self._apply_grouping()

    def set_group_fields(self, group_fields):
        """设置默认分组字段（有序），空列表表示不分组。"""
        self._group_fields = [f for f in (group_fields or []) if f]
        self._update_group_button_text()
        if self._all_data:
            self._apply_grouping()

    def set_record_count(self, total, group_count=None):
        """手动覆盖底部统计文本；group_count 缺省时按当前顶层组数。"""
        if group_count is None:
            group_count = len(self._grouped_roots)
        self._update_page_info(total, group_count)

    def get_data(self):
        return self._all_data

    def enable_context_menu(self, enable):
        self.tree_view.enable_context_menu(enable)

    def set_selection_mode(self, mode):
        self.tree_view.setSelectionMode(mode)

    def tool_bar_visible(self, flag):
        self.tool_bar.setVisible(flag)

    def set_no_data_text(self, text):
        self.tree_view.set_no_data_text(text)
        self.big_view.set_no_data_text(text)

    def set_search_pattern(self, pattern):
        self.search_line_edit.setText(pattern)

    def get_tree_view(self):
        return self.tree_view

    def get_big_view(self):
        return self.big_view

    # ---------- 分组核心 ----------
    def _group_label_of(self, data_obj):
        # 返回纯组名（不含计数），计数由 delegate 动态统计后追加
        return data_obj.get(GROUP_TEXT_KEY, "")

    def _build_display_map(self):
        """{字段key: display函数}，用于把组的原始值格式化成显示文本（如 1440→3.0天）。"""
        display_map = {}
        for h in self.header_list:
            key = h.get("key")
            disp = h.get("display")
            if key and callable(disp):
                display_map[key] = disp
        return display_map

    def _apply_grouping(self):
        tree_data = build_grouped_tree(
            self._all_data, self._group_fields, self._build_display_map())
        self._grouped_roots = tree_data if self._group_fields else []
        self.source_model.set_data_list(tree_data)
        self.big_view.setup_tree(tree_data, self._group_fields)
        if self._group_fields:
            self.tree_view.expandAll()
            self._expanded = True
        self._update_page_info(
            len(self._all_data), len(self._grouped_roots))

    def _update_page_info(self, total, group_count):
        if self._group_fields:
            self.page_info_label.setText(
                u"共计 {} 个 · 分 {} 组".format(total, group_count))
        else:
            self.page_info_label.setText(u"共计 {} 个".format(total))

    def _on_search(self, pattern):
        self.sort_filter_model.set_search_pattern(pattern)
        self.big_view.set_search_pattern(pattern)
        # 过滤后强制整块重绘，避免残留旧绘制（条纹）。组头跨整行已由 delegate 自绘，
        # 无需再设置 span。
        self.tree_view.viewport().update()

    def _show_group_menu(self):
        items = [{"label": h.get("label", h["key"]), "value": h["key"]}
                 for h in self.header_list if h.get("key")]
        if not items:
            return
        label_by_value = {it["value"]: it["label"] for it in items}
        value_by_label = {it["label"]: it["value"] for it in items}

        menu = MMenu(exclusive=False, parent=self.group_button)
        menu.set_data([it["label"] for it in items])
        menu.set_value([label_by_value[v] for v in self._group_fields
                        if v in label_by_value])

        def _on_changed(labels):
            labels = labels if isinstance(labels, list) else [labels]
            new_fields = [v for v in self._group_fields
                          if label_by_value.get(v) in labels]
            for lb in labels:
                v = value_by_label.get(lb)
                if v and v not in new_fields:
                    new_fields.append(v)
            self._group_fields = new_fields
            self._update_group_button_text()
            self._apply_grouping()

        menu.sig_value_changed.connect(_on_changed)
        menu.exec_(self.group_button.mapToGlobal(
            QtCore.QPoint(0, self.group_button.height())))

    def _update_group_button_text(self):
        label_by_value = {h["key"]: h.get("label", h["key"])
                          for h in self.header_list if h.get("key")}
        if not self._group_fields:
            self.group_button.setText("分组：无")
        else:
            names = [label_by_value.get(f, f) for f in self._group_fields]
            self.group_button.setText("分组：" + " › ".join(names))

    def _toggle_expand(self):
        self._expanded = not self._expanded
        if self._expanded:
            self.tree_view.expandAll()
        else:
            self.tree_view.collapseAll()
        self.big_view.set_all_expanded(self._expanded)

    # ---------- 事件 ----------
    def _toggle_group(self, index):
        # 折叠状态按"第 0 列"记录，必须用第 0 列兄弟节点查/设，
        # 否则隐藏第 0 列后点其它列会永远只展开、无法折叠。
        idx0 = index.sibling(index.row(), 0)
        self.tree_view.setExpanded(idx0, not self.tree_view.isExpanded(idx0))

    def slot_double_clicked(self, index):
        real_index = self.sort_filter_model.mapToSource(index)
        data_obj = real_index.internalPointer()
        if is_group_row(data_obj):
            self._toggle_group(index)
            return
        self.sig_double_clicked.emit(real_index)

    def slot_left_clicked(self, index):
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.LeftButton:
            return
        real_index = self.sort_filter_model.mapToSource(index)
        data_obj = real_index.internalPointer()
        if is_group_row(data_obj):
            # 组头行：单击即折叠/展开（原生箭头已关闭，靠这里驱动）
            self._toggle_group(index)
            return
        col = real_index.column()
        if 0 <= col < len(self.header_list) and self.header_list[col].get("is_link", False):
            self.sig_link_clicked.emit(real_index)
        else:
            self.sig_left_clicked.emit(real_index)
