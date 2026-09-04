# Import built-in modules
from collections.abc import Iterator
import re

# Import third-party modules
from Qt import QtCore
from Qt import QtGui

# Import local modules
from dayu_widgets.utils import apply_formatter
from dayu_widgets.utils import display_formatter
from dayu_widgets.utils import font_formatter
from dayu_widgets.utils import get_obj_value
from dayu_widgets.utils import icon_formatter
from dayu_widgets.utils import set_obj_value


SETTING_MAP = {
    QtCore.Qt.BackgroundRole: {"config": "bg_color", "formatter": QtGui.QColor},
    QtCore.Qt.DisplayRole: {"config": "display", "formatter": display_formatter},
    QtCore.Qt.EditRole: {"config": "edit", "formatter": None},
    QtCore.Qt.TextAlignmentRole: {
        "config": "alignment",
        "formatter": {
            "right": QtCore.Qt.AlignRight,
            "left": QtCore.Qt.AlignLeft,
            "center": QtCore.Qt.AlignCenter,
        },
    },
    QtCore.Qt.ForegroundRole: {"config": "color", "formatter": QtGui.QColor},
    QtCore.Qt.FontRole: {"config": "font", "formatter": font_formatter},
    QtCore.Qt.DecorationRole: {"config": "icon", "formatter": icon_formatter},
    QtCore.Qt.ToolTipRole: {"config": "tooltip", "formatter": display_formatter},
    QtCore.Qt.InitialSortOrderRole: {
        "config": "order",
        "formatter": {
            "asc": QtCore.Qt.AscendingOrder,
            "des": QtCore.Qt.DescendingOrder,
        },
    },
    QtCore.Qt.SizeHintRole: {
        "config": "size",
        "formatter": lambda args: QtCore.QSize(*args),
    },
    QtCore.Qt.UserRole: {"config": "data"},
}


class MTableModel(QtCore.QAbstractItemModel):
    checkStateChanged = QtCore.Signal(QtCore.QModelIndex, int)

    def __init__(self, parent=None, page_size=100, lazy_chunk_size=100):
        super(MTableModel, self).__init__(parent)
        self.temp_data = None
        self.root_item = {"name": "root", "children": []}
        self.data_generator = None
        self.header_list = []
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_lazy_load_timeout)
        self.use_slice = True
        self.use_delayed_loading = True
        self.page_size = page_size  # 分页粒度（仅 set_page 分页时使用）
        self.lazy_chunk_size = lazy_chunk_size  # 滚动懒加载块大小（默认懒加载，与分页粒度独立）
        self._paging_active = False  # 显式分页模式（set_page 驱动）时按页区间懒加载
        self._page_start = 0  # 当前页区间起点（分页模式）
        self._page_end = 0  # 当前页区间终点（分页模式）

        # 跟踪当前加载状态
        self._is_loading = False
        # 存储被延迟加载的节点的完整数据 {id(item): (item, full_children_list)}
        self._full_data_map = {}
        # 记录已经处理过（决定是否切片）的节点ID
        self._processed_nodes = set()
        # 标记数据是否已全部加载（用于搜索时临时禁用延迟加载）
        self._data_fully_loaded = False

        # 预编译 header 数组，加速 data() 热路径（list[index] 替代 dict.get）
        self._col_keys = []
        self._col_displays = []
        self._col_checkable = []

    def set_delayed_loading(self, enabled):
        """设置是否启用延迟加载"""
        self.use_delayed_loading = enabled

    def set_header_list(self, header_list):
        self.header_list = header_list
        # 预编译 header 字段为数组，data() 中 list[index] 替代 dict.get
        self._col_keys = [h.get("key") for h in header_list]
        self._col_displays = [h.get("display") for h in header_list]
        self._col_checkable = [h.get("checkable", False) for h in header_list]

    def _on_lazy_load_timeout(self):
        """Timer 槽函数：用有效的 QModelIndex 触发根节点懒加载"""
        self.fetchMore(QtCore.QModelIndex())

    def set_data_list(self, data_list, use_slice=True):
        self.use_slice = use_slice
        self._full_data_map.clear()
        self._processed_nodes.clear()
        self._data_fully_loaded = False

        if isinstance(data_list, Iterator):
            self.beginResetModel()
            self.root_item["children"] = []
            self.endResetModel()
            self.data_generator = data_list
            # 生成器模式下 temp_data 为 None（避免残留上一次列表数据干扰排序/搜索）
            self.temp_data = None
            self._original_temp_data = None
            self._paging_active = False
            self._page_start = 0
            self._page_end = 0
            if self.use_delayed_loading:
                self.timer.start(50)
            else:
                self.load_all_data()
        else:
            if isinstance(data_list, dict):
                # 单条 dict 视为单行数据
                data_list = [data_list]
            self.temp_data = list(data_list) if data_list else []
            # 预设置 _parent/_row，让 index() 热路径免于反复 dict 写入
            for row_index, item in enumerate(self.temp_data):
                set_obj_value(item, "_parent", self.root_item)
                set_obj_value(item, "_row", row_index)
            # 记录原始插入顺序快照（供 reset sort 恢复）
            self._original_temp_data = self.temp_data[:]
            # 新数据到来，退出显式分页模式，恢复滚动懒加载
            self._paging_active = False
            self._page_start = 0
            self._page_end = 0
            self.beginResetModel()
            if self.use_slice and self.use_delayed_loading:
                self.root_item["children"] = (
                    self.temp_data[: min(self.lazy_chunk_size, len(self.temp_data))] if self.temp_data else []
                )
            else:
                self.root_item["children"] = self.temp_data if self.temp_data else []
            self.endResetModel()
            self.data_generator = None
            self._is_loading = False

    def clear(self):
        self.beginResetModel()
        self.temp_data = []
        self.root_item["children"] = []
        self._full_data_map.clear()
        self._processed_nodes.clear()
        self._data_fully_loaded = False
        # 清空排序快照与分页状态，避免 reset sort 恢复出已清空的数据
        self._original_temp_data = None
        self._paging_active = False
        self._page_start = 0
        self._page_end = 0
        # 停止懒加载定时器并丢弃生成器，避免 clear 后旧生成器继续插入数据
        self.timer.stop()
        self.data_generator = None
        self.endResetModel()
        self._is_loading = False

    def set_page(self, page):
        """切换到指定页（use_slice 模式下的真实切片）。

        进入分页模式后，当前页数据按 lazy_chunk_size 块懒加载：
        初始只放页区间前 lazy_chunk_size 条，滚动到底通过 fetchMore 补全。
        """
        if not self.use_slice or self.temp_data is None:
            return
        if self.page_size <= 0:
            return
        if page < 1:
            page = 1
        total_page = max(1, (len(self.temp_data) + self.page_size - 1) // self.page_size)
        page = min(page, total_page)
        start = (page - 1) * self.page_size
        end = min(start + self.page_size, len(self.temp_data))
        self._page_start = start
        self._page_end = end
        self._paging_active = True
        self.beginResetModel()
        # 页内懒加载：初始只放页区间前 min(lazy_chunk_size, 页大小) 条，滚动时 fetchMore 补
        page_initial = min(self.lazy_chunk_size, self._page_end - self._page_start)
        self.root_item["children"] = self.temp_data[start : start + page_initial]
        self.endResetModel()

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        """QTableView/QTreeView 直接挂 MTableModel（不经 MSortFilterModel）时，
        点击表头会调用 model.sort()。QAbstractItemModel.sort 基类是空操作，
        这里转发到 sort_by_key 实现真实排序。

        :param column: 列号（对应 header_list 下标）；<0 表示 reset sort
        :param order: QtCore.Qt.AscendingOrder / QtCore.Qt.DescendingOrder
        """
        if column < 0:
            # reset sort（header_view 的 Reset Sort action）：恢复原始插入顺序
            self.restore_original_order()
            return
        if self.header_list and 0 <= column < len(self.header_list):
            key = self.header_list[column].get("key")
            if key:
                self.sort_by_key(key, order)

    def sort_by_key(self, key, order=QtCore.Qt.AscendingOrder):
        """在 Python 层对全量数据排序（C 级 sorted，比 QSortFilterProxyModel 逐行回调快数百倍）。
        :param key: 数据字段名
        :param order: QtCore.Qt.AscendingOrder / QtCore.Qt.DescendingOrder
        """
        if self.temp_data is None:
            return False
        reverse = order == QtCore.Qt.DescendingOrder

        def _sort_key(item):
            value = get_obj_value(item, key)
            # 三元组保证：None 永远在尾部（升序）、数值按数值、其它按字符串、混合类型不崩
            if value is None:
                return (1, 0, "")
            if isinstance(value, (int, float)):
                return (0, 0, value)
            return (0, 1, str(value))

        # 首次排序时保存原始插入顺序，供 reset sort（sort(-1)）恢复
        if getattr(self, "_original_temp_data", None) is None:
            self._original_temp_data = self.temp_data[:]

        # 整体排序：对整个数据集排序（Web 端标准做法），分页从排序后数据取
        self.temp_data.sort(key=_sort_key, reverse=reverse)
        self.beginResetModel()
        for row_index, item in enumerate(self.temp_data):
            set_obj_value(item, "_row", row_index)
        # 切片语义与 set_data_list/set_page 保持一致：
        # 分页模式显示排序后数据的当前页区间（页内懒加载）；搜索中（_data_fully_loaded）全量显示
        if getattr(self, "_paging_active", False):
            page_initial = min(self.lazy_chunk_size, self._page_end - self._page_start)
            self.root_item["children"] = self.temp_data[
                self._page_start : self._page_start + page_initial
            ]
        elif self.use_slice and self.use_delayed_loading and not self._data_fully_loaded:
            self.root_item["children"] = self.temp_data[: self.lazy_chunk_size]
        else:
            self.root_item["children"] = self.temp_data
        # 排序改变行序，先把被切片子节点的完整数据写回（否则清空 _full_data_map
        # 会导致已展开子节点的剩余数据永久丢失），再清理懒加载切片缓存
        for pid, (item, full_children) in self._full_data_map.items():
            set_obj_value(item, "children", full_children)
        self._full_data_map.clear()
        self._processed_nodes.clear()
        self.endResetModel()
        return True

    def restore_original_order(self):
        """恢复 set_data_list 时的原始插入顺序（供 reset sort 使用）。"""
        original = getattr(self, "_original_temp_data", None)
        if original is None or self.temp_data is None:
            return
        self.temp_data = original[:]
        self.beginResetModel()
        for row_index, item in enumerate(self.temp_data):
            set_obj_value(item, "_row", row_index)
        if getattr(self, "_paging_active", False):
            self.root_item["children"] = self.temp_data[
                self._page_start : min(self._page_start + self.lazy_chunk_size, self._page_end)
            ]
        elif self.use_slice and self.use_delayed_loading and not self._data_fully_loaded:
            self.root_item["children"] = self.temp_data[: self.lazy_chunk_size]
        else:
            self.root_item["children"] = self.temp_data
        # 与排序一致：先写回被切片子节点的完整数据再清缓存
        for pid, (item, full_children) in self._full_data_map.items():
            set_obj_value(item, "children", full_children)
        self._full_data_map.clear()
        self._processed_nodes.clear()
        self.endResetModel()

    def get_data_list(self):
        return self.temp_data

    def get_root_item_children(self):
        return self.root_item['children']

    def append(self, data_dict):
        if self.temp_data is None:
            self.temp_data = []
        if self.root_item["children"] is self.temp_data:
            # 全量模式：children 与 temp_data 是同一列表，只追加一次
            self.temp_data.append(data_dict)
        else:
            # 切片/懒加载模式：把新行插入到 children 末尾对应的 temp_data 位置，
            # 保持「children 是 temp_data 前缀」的性质，滚动加载顺序不被打乱
            insert_pos = len(self.root_item["children"])
            self.temp_data.insert(insert_pos, data_dict)
            self.root_item["children"].append(data_dict)
        # 同步原始顺序快照，保证 append 后再 reset sort 不会丢行
        if getattr(self, "_original_temp_data", None) is not None:
            self._original_temp_data.append(data_dict)
        # 不要在这里调用 fetchMore，这会干扰正常的加载逻辑
        self.layoutChanged.emit()  # 使用 layoutChanged 来通知视图更新

    def remove(self, data_dict):
        try:
            row = self.root_item["children"].index(data_dict)
        except ValueError:
            return
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        if self.temp_data:
            try:
                self.temp_data.remove(data_dict)
            except ValueError:
                pass
        # 全量模式下 children 与 temp_data 是同一列表（已删一次），切片模式才需要再删 children
        if self.root_item["children"] is not self.temp_data:
            del self.root_item["children"][row]
        # 同步原始顺序快照，保证 remove 后再 reset sort 不会复活已删行
        if getattr(self, "_original_temp_data", None) is not None:
            try:
                self._original_temp_data.remove(data_dict)
            except ValueError:
                pass
        self.endRemoveRows()

    def flags(self, index):
        result = QtCore.QAbstractItemModel.flags(self, index)
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        column = index.column()
        if column >= len(self.header_list):
            return result

        header_config = self.header_list[column]

        # 组头行（group_builder 构建的 _is_group_row 节点）不参与编辑/复选，
        # 否则 editable/selectable 列会在组头行触发 editor 弹出控件。
        data_obj = index.internalPointer()
        is_group_row = isinstance(data_obj, dict) and data_obj.get("_is_group_row") is True

        if is_group_row:
            return result & ~QtCore.Qt.ItemIsEditable

        if header_config.get("checkable", False):
            result |= QtCore.Qt.ItemIsUserCheckable
            data_obj = index.internalPointer()
            key = header_config.get("key")
            check_enabled = get_obj_value(data_obj, key + "_checkableEnabled")
            if check_enabled is not None and not check_enabled:
                result &= ~QtCore.Qt.ItemIsEnabled
        if header_config.get("selectable", False):
            result |= QtCore.Qt.ItemIsEditable
        if header_config.get("editable", False):
            result |= QtCore.Qt.ItemIsEditable
        if header_config.get("draggable", False):
            result |= QtCore.Qt.ItemIsDragEnabled
        if header_config.get("droppable", False):
            result |= QtCore.Qt.ItemIsDropEnabled

        return result

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Vertical:
            return super(MTableModel, self).headerData(section, orientation, role)
        if not self.header_list or section >= len(self.header_list):
            return None
        if role == QtCore.Qt.DisplayRole:
            return self.header_list[section]["label"]
        return None

    def index(self, row, column, parent_index=None):
        if not parent_index or not parent_index.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent_index.internalPointer()

        # 优化：直接字典访问代替 get_obj_value
        if isinstance(parent_item, dict):
            children_list = parent_item.get("children", [])
        else:
            children_list = getattr(parent_item, "children", [])

        if 0 <= row < len(children_list):
            child_item = children_list[row]
            if child_item:
                # Optimized: Assume _parent and _row are already set by set_data_list/fetchMore
                # We still check/set lazily just in case (e.g. dynamic modifications),
                # but we skip the expensive map check if _parent is already present.
                # 优化：直接访问
                if isinstance(child_item, dict):
                    has_parent = child_item.get("_parent") is not None
                else:
                    has_parent = getattr(child_item, "_parent", None) is not None

                if not has_parent:
                    set_obj_value(child_item, "_parent", parent_item)
                    set_obj_value(child_item, "_row", row)

                return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item = index.internalPointer()
        # 优化：直接访问
        if isinstance(child_item, dict):
            parent_item = child_item.get("_parent")
        else:
            parent_item = getattr(child_item, "_parent", None)

        # 注意：必须用 is 做身份比较——root_item 的 children 可能包含数万条数据，
        # 用 == 值比较会退化成 O(N)（甚至 O(N^2)），是平铺大数据下 parent() 的最大瓶颈
        if parent_item is None or parent_item is self.root_item:
            return QtCore.QModelIndex()

        # 找到父节点在祖父节点中的位置
        # 优化：直接访问
        if isinstance(parent_item, dict):
            grand_item = parent_item.get("_parent", self.root_item)
        else:
            grand_item = getattr(parent_item, "_parent", self.root_item)

        if isinstance(grand_item, dict):
            parent_list = grand_item.get("children", [])
        else:
            parent_list = getattr(grand_item, "children", [])

        # 尝试使用缓存的行索引优化查找性能 (O(1))
        if isinstance(parent_item, dict):
            row = parent_item.get("_row")
        else:
            row = getattr(parent_item, "_row", None)

        if row is not None and 0 <= row < len(parent_list):
            # 验证缓存的有效性
            if parent_list[row] is parent_item:
                return self.createIndex(row, 0, parent_item)

        # 缓存无效或不存在，回退到线性查找 (O(N))
        if parent_item in parent_list:
            row = parent_list.index(parent_item)
            # 更新缓存
            set_obj_value(parent_item, "_row", row)
            return self.createIndex(row, 0, parent_item)

        return QtCore.QModelIndex()

    def rowCount(self, parent_index=None):
        if parent_index and parent_index.isValid():
            parent_item = parent_index.internalPointer()
        else:
            parent_item = self.root_item

        # 优化：直接访问
        if isinstance(parent_item, dict):
            children_obj = parent_item.get("children", [])
        else:
            children_obj = getattr(parent_item, "children", [])

        # 延迟加载逻辑：如果是第一次访问且子项过多，进行切片
        # 只有在未完全加载模式下才进行切片
        if self.use_delayed_loading and not self._data_fully_loaded and parent_index and parent_index.isValid():
            pid = id(parent_item)
            if pid not in self._processed_nodes:
                if isinstance(children_obj, Iterator):
                    # children 可能被用户传入生成器（不常见但需兼容）
                    return 0
                if len(children_obj) > self.lazy_chunk_size:
                    self._full_data_map[pid] = (parent_item, children_obj)
                    sliced = children_obj[:self.lazy_chunk_size]
                    # 更新父对象的 children
                    set_obj_value(parent_item, "children", sliced)
                    children_obj = sliced
                self._processed_nodes.add(pid)

        # children_obj 可能被用户传入生成器（不常见但需兼容）
        if isinstance(children_obj, Iterator):
            return 0
        return len(children_obj)

    def hasChildren(self, parent_index=None):
        if parent_index and parent_index.isValid():
            parent_data = parent_index.internalPointer()
        else:
            parent_data = self.root_item

        # 优化：直接访问
        if isinstance(parent_data, dict):
            children_obj = parent_data.get("children", [])
        else:
            children_obj = getattr(parent_data, "children", [])

        # 生成器 children 无法求 len，与 rowCount 行为保持一致
        if isinstance(children_obj, Iterator):
            return False
        return len(children_obj) > 0

    def columnCount(self, parent_index=None):
        return len(self.header_list)

    def canFetchMore(self, index):
        if not self.use_delayed_loading:  # 如果不使用延迟加载，直接返回False
            return False

        if self._is_loading:
            return False

        if getattr(self, "_paging_active", False) and not index.isValid():
            # 显式分页模式：根节点按页区间懒加载，滚动到底只在页内补数据
            if self.temp_data is None:
                return False
            page_total = min(self._page_end, len(self.temp_data)) - self._page_start
            return len(self.root_item["children"]) < page_total

        if index.isValid():
            # 检查子节点是否可以加载更多
            item = index.internalPointer()
            if id(item) in self._full_data_map:
                item, full_children = self._full_data_map[id(item)]
                current_children = get_obj_value(item, "children", [])
                return len(current_children) < len(full_children)
            return False
        else:
            # 检查根节点是否可以加载更多
            if self.data_generator and not self._data_fully_loaded:
                return True
            if self.temp_data and len(self.root_item["children"]) < len(self.temp_data):
                return True
        return False

    def fetchMore(self, index=None):
        if index is None:
            index = QtCore.QModelIndex()

        if not self.use_delayed_loading:  # 如果不使用延迟加载，直接返回
            return

        if self._is_loading:
            return

        self._is_loading = True

        try:
            if index.isValid():
                # 加载子节点数据
                parent_item = index.internalPointer()
                pid = id(parent_item)
                if pid in self._full_data_map:
                    _item, full_children = self._full_data_map[pid]
                    current_children = get_obj_value(parent_item, "children", [])
                    current_count = len(current_children)
                    remaining = len(full_children) - current_count
                    items_to_fetch = min(self.lazy_chunk_size, remaining)

                    if items_to_fetch > 0:
                        self.beginInsertRows(index, current_count, current_count + items_to_fetch - 1)
                        new_data = full_children[current_count: current_count + items_to_fetch]
                        current_children.extend(new_data)
                        self.endInsertRows()
            else:
                # 加载根节点数据
                if getattr(self, "_paging_active", False):
                    # 分页模式：只在当前页区间内继续懒加载
                    limit = min(self._page_end, len(self.temp_data))
                    current_count = len(self.root_item["children"])
                    remaining = limit - self._page_start - current_count
                    items_to_fetch = min(self.lazy_chunk_size, remaining)
                    slice_start = self._page_start + current_count

                    if items_to_fetch > 0:
                        for offset, item in enumerate(
                            self.temp_data[slice_start : slice_start + items_to_fetch]
                        ):
                            set_obj_value(item, "_parent", self.root_item)
                            set_obj_value(item, "_row", slice_start + offset)
                        self.beginInsertRows(QtCore.QModelIndex(), current_count, current_count + items_to_fetch - 1)
                        self.root_item["children"].extend(
                            self.temp_data[slice_start : slice_start + items_to_fetch]
                        )
                        self.endInsertRows()
                elif self.data_generator:
                    new_data = []
                    for _ in range(self.lazy_chunk_size):
                        try:
                            new_data.append(next(self.data_generator))
                        except StopIteration:
                            break

                    if new_data:
                        current_count = len(self.root_item["children"])
                        for offset, item in enumerate(new_data):
                            set_obj_value(item, "_parent", self.root_item)
                            set_obj_value(item, "_row", current_count + offset)
                        self.beginInsertRows(QtCore.QModelIndex(), current_count, current_count + len(new_data) - 1)
                        self.root_item["children"].extend(new_data)
                        self.endInsertRows()

                    if len(new_data) < self.lazy_chunk_size:
                        if self.timer.isActive():
                            self.timer.stop()
                        # 生成器已耗尽，置 None 防止 canFetchMore 永远返回 True 导致空转
                        self.data_generator = None

                elif self.temp_data and len(self.root_item["children"]) < len(self.temp_data):
                    current_count = len(self.root_item["children"])
                    remaining = len(self.temp_data) - current_count
                    items_to_fetch = min(self.lazy_chunk_size, remaining)

                    if items_to_fetch > 0:
                        self.beginInsertRows(QtCore.QModelIndex(), current_count, current_count + items_to_fetch - 1)
                        new_data = self.temp_data[current_count: current_count + items_to_fetch]
                        self.root_item["children"].extend(new_data)
                        self.endInsertRows()

        finally:
            self._is_loading = False

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        column = index.column()
        # 边界检查虽然必要，但如果能保证调用者行为良好，可酌情简化，这里保留以防万一
        if column >= len(self.header_list):
            return None

        attr_dict = self.header_list[column]
        # 直接访问 internalPointer，假设它是 dict
        data_obj = index.internalPointer()

        # 组头行（group_builder 的 _is_group_row 节点）不参与数据 role 渲染：
        # 组头整行由组头 delegate 自绘，任何 BackgroundRole/FontRole/DecorationRole/
        # ForegroundRole 的 formatter 都会收到 None 值，可能崩溃或给组头染上数据色。
        if isinstance(data_obj, dict) and data_obj.get("_is_group_row") is True:
            return None

        # 1. 快速路径：DisplayRole / EditRole
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            attr = self._col_keys[column]
            # 使用 dict.get 直接获取值，比 get_obj_value 少一层函数调用
            # 注意：这里假设 data_obj 是 dict。如果是对象，需保持 get_obj_value
            # 为了兼容性，我们还是手动内联 get_obj_value 的核心逻辑：
            if isinstance(data_obj, dict):
                value = data_obj.get(attr)
            else:
                value = getattr(data_obj, attr, None)

            # EditRole 返回原始值：编辑器应拿到未格式化的数据（如 12 而非 "12 岁"），
            # 否则 display formatter 会在每次编辑往返中重复叠加（"12 岁" -> "12 岁 岁"）。
            if role == QtCore.Qt.EditRole:
                return value

            # DisplayRole 应用 display formatter
            formatter = self._col_displays[column]
            if formatter:
                return apply_formatter(formatter, value, data_obj)
            return value

        # 2. 处理 CheckStateRole
        if role == QtCore.Qt.CheckStateRole:
            if self._col_checkable[column]:
                attr = self._col_keys[column]
                key = f"{attr}_checked"
                if isinstance(data_obj, dict):
                    state = data_obj.get(key)
                else:
                    state = getattr(data_obj, key, None)
                # 归一化：Python bool 不应被渲染成半选（True == PartiallyChecked 的整数值 1）
                if state is None or state is False:
                    return QtCore.Qt.Unchecked
                if state is True:
                    return QtCore.Qt.Checked
                return state
            return None

        # 3. 处理其他角色 (Generic path)
        if role in SETTING_MAP:
            role_config = SETTING_MAP[role]
            role_key = role_config.get("config")
            formatter_from_config = attr_dict.get(role_key)

            # 快速跳过不需要处理的情况
            if not formatter_from_config and role != QtCore.Qt.ToolTipRole:
                return None

            attr = self._col_keys[column]
            if isinstance(data_obj, dict):
                value = data_obj.get(attr)
            else:
                value = getattr(data_obj, attr, None)

            if formatter_from_config:
                value = apply_formatter(formatter_from_config, value, data_obj)

            formatter_from_model = role_config.get("formatter")
            if formatter_from_model:
                value = apply_formatter(formatter_from_model, value)
            return value

        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid() and role in [QtCore.Qt.CheckStateRole, QtCore.Qt.EditRole]:
            column = index.column()
            if column >= len(self.header_list):
                return False

            attr_dict = self.header_list[column]
            key = attr_dict.get("key")
            data_obj = index.internalPointer()

            if role == QtCore.Qt.CheckStateRole and attr_dict.get("checkable", False):
                key += "_checked"
                set_obj_value(data_obj, key, value)
                self.dataChanged.emit(index, index, [role])
                self.checkStateChanged.emit(index, value)

                # 更新children
                children = get_obj_value(data_obj, "children", [])
                for row, sub_obj in enumerate(children):
                    set_obj_value(sub_obj, key, value)
                    sub_index = self.index(row, index.column(), index)
                    if sub_index.isValid():
                        self.dataChanged.emit(sub_index, sub_index, [role])
                        self.checkStateChanged.emit(sub_index, value)

                # 更新parent
                parent_index = index.parent()
                if parent_index.isValid():
                    parent_obj = parent_index.internalPointer()
                    new_parent_value = value
                    old_parent_value = get_obj_value(parent_obj, key)

                    parent_children = get_obj_value(get_obj_value(data_obj, "_parent"), "children", [])
                    for sibling_obj in parent_children:
                        if value != get_obj_value(sibling_obj, key):
                            new_parent_value = 1  # PartiallyChecked
                            break

                    if new_parent_value != old_parent_value:
                        set_obj_value(parent_obj, key, new_parent_value)
                        self.dataChanged.emit(parent_index, parent_index, [role])
            else:
                set_obj_value(data_obj, key, value)
                self.dataChanged.emit(index, index, [role])

            return True
        return False

    def load_all_data(self):
        if self._data_fully_loaded:
            return

        # 搜索等需要全量数据的场景：退出显式分页模式，避免按页区间偏移展开造成重复/缺失
        self._paging_active = False
        self._page_start = 0
        self._page_end = 0

        # 标记为已完全加载，后续 rowCount 不再进行切片
        self._data_fully_loaded = True

        # 1. 恢复根节点数据
        if self.data_generator:
            new_data = list(self.data_generator)  # C 层循环，比手工 while/StopIteration 更快
            self.data_generator = None  # 已消费完，防止 canFetchMore 永远返回 True
            if new_data:
                current_count = len(self.root_item["children"])
                for offset, item in enumerate(new_data):
                    set_obj_value(item, "_parent", self.root_item)
                    set_obj_value(item, "_row", current_count + offset)
                self.beginInsertRows(QtCore.QModelIndex(), current_count, current_count + len(new_data) - 1)
                self.root_item["children"].extend(new_data)
                self.endInsertRows()
        elif self.temp_data:
            # 全量替换 children：分页模式下 children 是页区间切片（非前缀），
            # 增量 extend 会与页区间重叠/错位，必须整体重建
            self.beginResetModel()
            for row_index, item in enumerate(self.temp_data):
                set_obj_value(item, "_parent", self.root_item)
                set_obj_value(item, "_row", row_index)
            self.root_item["children"] = self.temp_data
            self.endResetModel()

        # 2. 恢复所有被切片的子节点数据
        if self._full_data_map:
            # 注意：这里我们不发送 beginInsertRows/endInsertRows，因为可能涉及多个父节点
            # 调用 layoutChanged 让视图重新从模型获取数据更简单且安全
            self.layoutAboutToBeChanged.emit()
            for pid, (item, full_children) in self._full_data_map.items():
                set_obj_value(item, "children", full_children)
            # 不清理 _full_data_map，保留用于 restore_lazy_mode 重新切片
            # 注意：我们不清除 _processed_nodes，以防 rowCount 再次切片
            self.layoutChanged.emit()

    def restore_lazy_mode(self):
        """恢复延迟加载模式（用于搜索结束后）"""
        if not self._data_fully_loaded:
            return

        self.beginResetModel()
        self._data_fully_loaded = False
        self._processed_nodes.clear()
        # 复位分页状态：搜索结束后回到纯懒加载（分页由调用方按需重建）
        self._paging_active = False
        self._page_start = 0
        self._page_end = 0

        # 对根节点重新切片
        current_children = self.root_item["children"]
        if len(current_children) > self.lazy_chunk_size:
            # 生成器已被消费（data_generator=None）时，把已加载的完整数据存入 temp_data，
            # 否则后续 canFetchMore/fetchMore 无法继续加载剩余数据
            if self.temp_data is None:
                self.temp_data = current_children[:]
            # 保存完整数据到 _full_data_map（如果还没有）
            rid = id(self.root_item)
            if rid not in self._full_data_map:
                self._full_data_map[rid] = (self.root_item, current_children)
            self.root_item["children"] = current_children[: self.lazy_chunk_size]

        # 递归对所有已展开的子节点重新切片
        def _re_slice_node(node_item):
            node_children = get_obj_value(node_item, "children", [])
            if len(node_children) > self.lazy_chunk_size:
                nid = id(node_item)
                if nid not in self._full_data_map:
                    self._full_data_map[nid] = (node_item, node_children)
                set_obj_value(node_item, "children", node_children[: self.lazy_chunk_size])
                # 递归处理可见子节点（可能之前也被展开了）
                for child in node_children[: self.lazy_chunk_size]:
                    _re_slice_node(child)

        for item in self.root_item["children"][: self.lazy_chunk_size]:
            _re_slice_node(item)

        self.endResetModel()


class MSortFilterModel(QtCore.QSortFilterProxyModel):
    filter_finished = QtCore.Signal()
    sort_finished = QtCore.Signal()

    def __init__(self, parent=None):
        super(MSortFilterModel, self).__init__(parent)
        self.header_list = []

        # 过滤与排序缓存
        self._search_terms = []
        self._search_terms_set = None  # 预计算的 set，避免 _matches_filter 中每行创建
        self._searchable_columns = []
        self._filter_columns = []
        self._cached_filter_results = {}  # 缓存过滤结果
        self._is_filtering = False

        # 添加延迟过滤功能
        self._filter_timer = QtCore.QTimer(self)
        self._filter_timer.setSingleShot(True)  # 单次触发
        self._filter_timer.timeout.connect(self._apply_delayed_filter)
        self._pending_search_pattern = ""
        self._pending_filter_patterns = {}  # 存储延迟的过滤模式

        # 新增：控制是否使用延迟过滤
        self.use_delayed_filtering = True
        self._filter_delay_ms = 300  # 延迟时间，可配置
        self._filtering_enabled = False

    def set_delayed_filtering(self, enabled, delay_ms=300):
        """设置是否启用延迟过滤以及延迟时间"""
        self.use_delayed_filtering = enabled
        self._filter_delay_ms = delay_ms

    def set_header_list(self, header_list):
        self.header_list = header_list
        # 预计算搜索和过滤相关的列
        self._searchable_columns = [
            (i, header) for i, header in enumerate(self.header_list)
            if header.get("searchable", False)
        ]
        self._filter_columns = [
            (i, header) for i, header in enumerate(self.header_list)
            if header.get("reg") is not None
        ]

        for head in self.header_list:
            head.setdefault("reg", None)

    def _matches_filter(self, source_row, source_parent):
        """检查单行是否匹配过滤条件（不递归）"""
        source_model = self.sourceModel()
        get_index = source_model.index
        get_data = source_model.data

        search_terms = self._search_terms
        # 1. 搜索过滤优化
        if search_terms:
            # 优化：只需遍历一次列，检查所有搜索词
            # 逻辑：所有搜索词都必须被找到（AND关系），但可以分布在不同列中
            # 使用预计算的 set，避免每行重新 hash 搜索词（大列表下显著提升性能）
            remaining_terms = set(self._search_terms_set) if self._search_terms_set else set()

            for col, header_config in self._searchable_columns:
                if not remaining_terms:
                    break

                model_index = get_index(source_row, col, source_parent)
                value = get_data(model_index)
                if value is None:
                    continue

                # 预计算小写字符串，避免对每个term重复计算
                value_str = str(value).lower()

                # 检查剩余的term
                found_in_col = []
                for term in remaining_terms:
                    if term in value_str:
                        found_in_col.append(term)

                # 从待查找集合中移除已找到的term
                for term in found_in_col:
                    remaining_terms.remove(term)

            if remaining_terms:
                return False

        # 2. 列过滤优化
        for col, header_config in self._filter_columns:
            reg_exp = header_config.get("reg")

            if reg_exp is None:  # 没有设置过滤模式，跳过
                continue

            model_index = get_index(source_row, col, source_parent)
            value = get_data(model_index)
            if value is None:
                return False

            if isinstance(value, str):
                # 对于多标签的情况，使用any而不是all，更高效
                values = [v.strip() for v in value.split(',') if v.strip()]
                if values:
                    match_found = False
                    for v in values:
                        if reg_exp.search(v):
                            match_found = True
                            break
                    if not match_found:
                        return False
                else:
                    # 空字符串的情况
                    if not reg_exp.search(""):
                        return False
            else:
                value_str = str(value)
                if not reg_exp.search(value_str):
                    return False

        return True

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filtering_enabled:
            return True
        # Generate a unique key for the row in the tree structure
        parent_id = source_parent.internalId() if source_parent.isValid() else 0
        cache_key = (source_row, parent_id)

        # 如果正在过滤，快速返回缓存结果
        if self._is_filtering and cache_key in self._cached_filter_results:
            return self._cached_filter_results[cache_key]

        # 1. 检查自身是否匹配
        if self._matches_filter(source_row, source_parent):
            if self._is_filtering:
                self._cached_filter_results[cache_key] = True
            return True

        # 2. 如果自身不匹配，检查是否有任何子项匹配（手动递归）
        source_model = self.sourceModel()
        current_index = source_model.index(source_row, 0, source_parent)

        if source_model.hasChildren(current_index):
            # 遍历所有子行
            rows = source_model.rowCount(current_index)
            for i in range(rows):
                if self.filterAcceptsRow(i, current_index):
                    # 只要有一个子项匹配，保留父项
                    if self._is_filtering:
                        self._cached_filter_results[cache_key] = True
                    return True

        # 自身和子项都不匹配
        if self._is_filtering:
            self._cached_filter_results[cache_key] = False
        return False

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        """重写排序：对 MTableModel 走 Python 级排序（C 级 sorted），避免
        QSortFilterProxyModel 逐行 Python 回调（3 万行 2s -> ~70ms）。
        非 MTableModel 源退回基类实现。
        """
        source = self.sourceModel()
        if isinstance(source, MTableModel) and column < 0:
            # reset sort：恢复 set_data_list 时的原始插入顺序
            source.restore_original_order()
            self._cached_filter_results.clear()
            self.setDynamicSortFilter(False)
            super(MSortFilterModel, self).sort(-1, QtCore.Qt.AscendingOrder)
            self.sort_finished.emit()
            return
        if (
            isinstance(source, MTableModel)
            and self.header_list
            and 0 <= column < len(self.header_list)
        ):
            key = self.header_list[column].get("key")
            if key and source.sort_by_key(key, order):
                self._cached_filter_results.clear()
                # 数据已在源模型层排好序；关闭 proxy 自身的动态排序并清掉其残留排序状态
                # （否则 proxy 会用 set_header_list 时残留的旧排序状态把显示再排一遍，
                #   导致"源数据降序、表格却升序显示"以及跨列排序错乱）
                self.setDynamicSortFilter(False)
                super(MSortFilterModel, self).sort(-1, QtCore.Qt.AscendingOrder)
                self.sort_finished.emit()
                return
        super(MSortFilterModel, self).sort(column, order)

    def set_search_pattern(self, pattern):
        """设置搜索模式，根据配置决定是否延迟"""
        if not self.use_delayed_filtering:
            # 如果不使用延迟过滤，立即应用
            self._apply_filter_immediately(pattern, {})
        else:
            # 使用延迟过滤
            self._pending_search_pattern = pattern
            # 重置计时器以实现防抖
            if self._filter_timer.isActive():
                self._filter_timer.stop()
            self._filter_timer.start(self._filter_delay_ms)

    def set_filter_attr_pattern(self, attr, pattern):
        """设置属性过滤模式，根据配置决定是否延迟"""
        if not self.use_delayed_filtering:
            # 如果不使用延迟过滤，立即应用
            patterns = {attr: pattern}
            self._apply_filter_immediately(self._pending_search_pattern, patterns)
        else:
            # 使用延迟过滤
            self._pending_filter_patterns[attr] = pattern
            # 重置计时器以实现防抖
            if self._filter_timer.isActive():
                self._filter_timer.stop()
            self._filter_timer.start(self._filter_delay_ms)

    def _apply_filter_immediately(self, pattern, filter_patterns):
        """立即应用过滤设置"""
        # 预处理搜索词
        pattern_lower = pattern.lower()
        self._search_terms = [term for term in pattern_lower.split() if term]
        self._search_terms_set = set(self._search_terms) if self._search_terms else None  # 预计算避免每行重复 hash

        # 应用属性过滤模式
        has_column_filter = False
        for attr, p_val in filter_patterns.items():
            for i, data_dict in enumerate(self.header_list):
                if data_dict.get("key") == attr:
                    # 直接设置正则模式（re 对象，忽略大小写）
                    data_dict["reg"] = re.compile(p_val, re.IGNORECASE) if p_val else None
                    if p_val:
                        has_column_filter = True
                    break

        # 检查是否还有其他列过滤器处于激活状态
        if not has_column_filter:
            for data_dict in self.header_list:
                reg = data_dict.get("reg")
                if reg and reg.pattern:
                    has_column_filter = True
                    break

        # 判断是否处于过滤状态
        is_filtering = bool(self._search_terms or has_column_filter)
        self._filtering_enabled = is_filtering

        # 只有在过滤时才需要加载所有数据
        if is_filtering:
            source_model = self.sourceModel()
            if isinstance(source_model, MTableModel):
                source_model.load_all_data()
        else:
            # 搜索结束，恢复延迟加载模式以提升性能
            source_model = self.sourceModel()
            if isinstance(source_model, MTableModel):
                source_model.restore_lazy_mode()

        self._update_filter_columns_cache()

        if is_filtering:
            self._is_filtering = True
            self._cached_filter_results.clear()

        # 必须调用 invalidateFilter 以触发重新过滤，无论 enabled 状态是否改变
        self.invalidateFilter()

        if is_filtering:
            self._is_filtering = False
        # 清空待处理模式
        self._pending_search_pattern = ""
        self._pending_filter_patterns.clear()
        self.filter_finished.emit()

    def _apply_delayed_filter(self):
        """应用延迟的过滤设置"""
        self._apply_filter_immediately(self._pending_search_pattern, self._pending_filter_patterns)

    def _update_filter_columns_cache(self):
        """更新过滤列的缓存"""
        self._filter_columns = [
            (i, header) for i, header in enumerate(self.header_list)
            if header.get("reg") and header["reg"].pattern
        ]

    def invalidateFilter(self):
        """重写invalidateFilter以优化性能"""
        # 在真正失效前进行一些预处理
        if not self._is_filtering:
            self._cached_filter_results.clear()

        super(MSortFilterModel, self).invalidateFilter()

    # 添加批量操作的方法
    def begin_filter_batch(self):
        """开始批量过滤操作"""
        self._is_filtering = True
        self._cached_filter_results.clear()

    def end_filter_batch(self):
        """结束批量过滤操作"""
        self._is_filtering = False
        self.invalidateFilter()

    def force_apply_filter(self):
        """立即应用所有延迟的过滤设置"""
        if self._filter_timer.isActive():
            self._filter_timer.stop()
        self._apply_delayed_filter()
