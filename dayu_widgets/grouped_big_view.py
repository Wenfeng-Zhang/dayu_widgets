# -*- coding: utf-8 -*-
"""分组大图视图（在 Big View 缩略图基础上按字段分组）。

MBigView 本质是 QListView（扁平），无法直接渲染树形分组数据。因此这里用
「滚动区 + 每个分组一个独立的小 MBigView」的方式实现分组大图：

    ┌─ 组头(灰底, 可折叠)  赛季A (12)
    │    [缩略图] [缩略图] [缩略图] ...   ← 该组的 MBigView
    ├─ 组头  赛季B (8)
    │    [缩略图] [缩略图] ...
    ...

要点：
  - 大图只展示【有缩略图】的数据行（默认 image 字段非空，可用 set_image_field 配置）；
    没有图的行不进大图，整组都没有图则该组不显示。
  - 组头计数是【动态】的：等于该组下当前可见（经搜索过滤后）的有图行数，
    搜索时实时更新；某组过滤后为 0 则整组隐藏。
  - 支持多字段嵌套：组头逐层缩进，点击组头折叠/展开整组。

信号：
    sig_double_clicked(QModelIndex)   叶子被双击（发的是源模型 index，internalPointer=row_dict）
    sig_left_clicked(QModelIndex)     叶子被左键点击
    sig_context_menu(object)          右键菜单事件（event.selection 为 row_dict 列表）
"""
# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.group_builder import GROUP_TEXT_KEY
from dayu_widgets.group_builder import is_group_row
from dayu_widgets.item_model import MSortFilterModel
from dayu_widgets.item_model import MTableModel
from dayu_widgets.item_view import MBigView
from dayu_widgets.qt import get_scale_factor


# 与表格组头一致：阶梯背景(逐层变亮) + 彩色左边条(随层级)
_BG_PALETTE = ["#3d4653", "#474747", "#565656", "#646464", "#727272"]
_ACCENT_PALETTE = ["#4a90d9", "#57a86b", "#d0a13a", "#b06bd0", "#d06b6b"]


def _pick(palette, level):
    return palette[min(max(level, 0), len(palette) - 1)]


class _GroupHeader(QtWidgets.QWidget):
    """可点击折叠的组头（阶梯灰底 + 彩色左边条 + 白字 + 三角箭头）。"""

    clicked = QtCore.Signal()

    def __init__(self, text, level, parent=None):
        super(_GroupHeader, self).__init__(parent)
        self._expanded = True
        bg = _pick(_BG_PALETTE, level)
        accent = _pick(_ACCENT_PALETTE, level)
        # 纯 QWidget 上 setStyleSheet 背景色默认不生效，必须开 WA_StyledBackground。
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setObjectName("GroupHeader")
        # 子 QLabel 必须显式设透明背景，否则会被全局主题 qss 加上默认背景。
        self.setStyleSheet(
            "#GroupHeader { background-color: %s;"
            " border-left: 3px solid %s;"
            " border-bottom: 1px solid #2a2a2a; }"
            "#GroupHeader QLabel { background: transparent; color: #ffffff;"
            " font-weight: bold; border: none; }" % (bg, accent))
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(28)

        lay = QtWidgets.QHBoxLayout(self)
        # 逐层增加左缩进，配合彩色边条形成明显的父/子层级
        lay.setContentsMargins(10 + max(level, 0) * 22, 2, 6, 2)
        lay.setSpacing(6)
        self.arrow_label = QtWidgets.QLabel(u"\u25bc")   # ▼
        self.text_label = QtWidgets.QLabel(text)
        lay.addWidget(self.arrow_label)
        lay.addWidget(self.text_label)
        lay.addStretch()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super(_GroupHeader, self).mousePressEvent(event)

    def set_text(self, text):
        self.text_label.setText(text)

    def set_expanded(self, expanded):
        self._expanded = expanded
        self.arrow_label.setText(u"\u25bc" if expanded else u"\u25b6")  # ▼ / ▶

    def is_expanded(self):
        return self._expanded


class GroupedBigView(QtWidgets.QScrollArea):
    sig_double_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_left_clicked = QtCore.Signal(QtCore.QModelIndex)
    sig_context_menu = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(GroupedBigView, self).__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self._header_list = []
        self._image_field = "image"
        self._no_data_text = "no data"
        default = dayu_theme.big_view_default_size
        self._icon_size = QtCore.QSize(default, default)

        self._sections = []      # [{"view": MBigView, "proxy": MSortFilterModel}]
        # 每个组头一条记录：{"header","container","text"(纯组名),"proxies"(该组下所有叶子section的proxy)}
        self._headers = []

        self._inner = QtWidgets.QWidget()
        self._lay = QtWidgets.QVBoxLayout(self._inner)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        self._lay.addStretch()
        self.setWidget(self._inner)

    # ---------- 接口 ----------
    def set_header_list(self, header_list):
        self._header_list = header_list

    def set_image_field(self, field):
        """设置数据行里缩略图字段名（默认 "image"）。"""
        self._image_field = field

    def set_icon_size(self, size):
        self._icon_size = size
        for sec in self._sections:
            sec["view"].setIconSize(size)
        self._refit_all()

    def set_no_data_text(self, text):
        self._no_data_text = text

    def set_search_pattern(self, pattern):
        for sec in self._sections:
            sec["proxy"].set_search_pattern(pattern)
        self._update_header_counts()
        self._refit_all()

    def set_all_expanded(self, expanded):
        for entry in self._headers:
            entry["header"].set_expanded(expanded)
        self._update_header_counts()
        self._refit_all()

    def setup_tree(self, tree_data, group_fields):
        """tree_data 为 group_builder.build_grouped_tree 的结果。"""
        self._clear()
        group_fields = [f for f in (group_fields or []) if f]
        if not group_fields:
            # 不分组：单个大图铺满（只放有图的行）
            rows = [r for r in (tree_data or []) if self._has_image(r)]
            view, _ = self._make_big_view(rows)
            self._add_widget(self._lay, view)
        else:
            self._render_nodes(tree_data or [], 0, self._lay)
        self._update_header_counts()
        self._refit_all()

    # ---------- 内部 ----------
    def _has_image(self, row):
        """数据行是否有缩略图：指定图片字段非空（icon 是本地路径、恒有值，不能用来判断）。"""
        return isinstance(row, dict) and bool(row.get(self._image_field))

    def _add_widget(self, layout, widget):
        # 顶层布局末尾有个 stretch，要插在它前面；嵌套容器直接 append
        if layout is self._lay:
            layout.insertWidget(layout.count() - 1, widget)
        else:
            layout.addWidget(widget)

    def _clear(self):
        while self._lay.count() > 1:   # 保留末尾 stretch
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._sections = []
        self._headers = []

    def _render_nodes(self, nodes, level, parent_layout):
        """渲染一层组，返回本层（含所有后代）创建的叶子 section 的 proxy 列表。

        没有任何有图行的组会被整组跳过（不加组头）。
        """
        created = []
        for node in nodes:
            if not is_group_row(node):
                continue
            children = node.get("children") or []
            container = QtWidgets.QWidget()
            clay = QtWidgets.QVBoxLayout(container)
            clay.setContentsMargins(0, 0, 0, 0)
            clay.setSpacing(0)

            if children and is_group_row(children[0]):
                child_proxies = self._render_nodes(children, level + 1, clay)
            else:
                img_rows = [r for r in children if self._has_image(r)]
                if img_rows:
                    view, proxy = self._make_big_view(img_rows)
                    clay.addWidget(view)
                    child_proxies = [proxy]
                else:
                    child_proxies = []

            if not child_proxies:
                container.deleteLater()   # 整组没有图 → 不显示
                continue

            header = _GroupHeader(node.get(GROUP_TEXT_KEY, ""), level)
            entry = {
                "header": header,
                "container": container,
                "text": node.get(GROUP_TEXT_KEY, ""),
                "proxies": child_proxies,
            }

            def _toggle(e=entry):
                e["header"].set_expanded(not e["header"].is_expanded())
                self._update_header_counts()
                self._refit_all()
            header.clicked.connect(_toggle)

            self._headers.append(entry)
            self._add_widget(parent_layout, header)
            self._add_widget(parent_layout, container)
            created.extend(child_proxies)
        return created

    def _make_big_view(self, rows):
        view = MBigView()
        view.setWordWrap(True)
        view.setFlow(QtWidgets.QListView.LeftToRight)
        view.setWrapping(True)
        view.setMovement(QtWidgets.QListView.Static)
        view.setResizeMode(QtWidgets.QListView.Adjust)
        view.setIconSize(self._icon_size)
        view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        source_model = MTableModel()
        proxy = MSortFilterModel()
        proxy.setSourceModel(source_model)
        if self._header_list:
            source_model.set_header_list(self._header_list)
            proxy.set_header_list(self._header_list)
            view.set_header_list(self._header_list)
        source_model.set_data_list(list(rows or []))
        view.setModel(proxy)

        view.set_no_data_text(self._no_data_text)
        view.enable_context_menu(True)
        view.sig_context_menu.connect(self.sig_context_menu)
        view.doubleClicked.connect(
            lambda idx, p=proxy: self._emit_leaf(self.sig_double_clicked, p, idx))
        view.pressed.connect(
            lambda idx, p=proxy: self._on_pressed(p, idx))

        self._sections.append({"view": view, "proxy": proxy})
        return view, proxy

    def _emit_leaf(self, signal, proxy, proxy_index):
        src = proxy.mapToSource(proxy_index)
        obj = src.internalPointer()
        if is_group_row(obj):
            return
        signal.emit(src)

    def _on_pressed(self, proxy, proxy_index):
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.LeftButton:
            return
        self._emit_leaf(self.sig_left_clicked, proxy, proxy_index)

    # ---------- 计数（动态）与高度自适应 ----------
    def _entry_count(self, entry):
        return sum(p.rowCount() for p in entry["proxies"])

    def _update_header_counts(self):
        """组头计数=该组下当前可见的有图行数；过滤后为 0 则整组隐藏。"""
        for entry in self._headers:
            cnt = self._entry_count(entry)
            entry["header"].set_text(u"{}  ({})".format(entry["text"], cnt))
            has = cnt > 0
            entry["header"].setVisible(has)
            entry["container"].setVisible(has and entry["header"].is_expanded())

    def _refit_all(self):
        scale_x, _ = get_scale_factor()
        avail = max(self.viewport().width() - 24, 100)
        cell_w = self._icon_size.width() + 10 * 2 + int(20 * scale_x)
        cell_h = self._icon_size.height() + 10 * 2 + int(30 * scale_x)
        cols = max(1, int(avail / cell_w))
        for sec in self._sections:
            view = sec["view"]
            visible = view.model().rowCount()   # 经 proxy 过滤后的可见数
            rows = (visible + cols - 1) // cols if visible else 0
            height = rows * cell_h + 12
            view.setFixedHeight(max(height, cell_h if visible else 10))

    def resizeEvent(self, event):
        super(GroupedBigView, self).resizeEvent(event)
        self._refit_all()
