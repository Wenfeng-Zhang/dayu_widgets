# -*- coding: utf-8 -*-
"""
Test MTableModel / MSortFilterModel core behaviours.

重点覆盖曾经修复过的回归点，避免后续重构把这些 bug 重新引入：
  - EditRole 返回原始值（display formatter 不会在编辑往返中叠加单位）
  - 组头行（_is_group_row）不可编辑、不参与任何数据 role 渲染
  - set_header_list 不会清空调用方预置的 reg
  - 排序：None 恒置尾、restore_original_order 可恢复插入顺序
  - 分页：set_page 越界钳制
  - 列过滤：re.search 子串语义；搜索词多词 AND
"""

# Import built-in modules
import re

# Import third-party modules
from Qt import QtCore

# Import local modules
from dayu_widgets import group_builder
from dayu_widgets.item_model import MSortFilterModel
from dayu_widgets.item_model import MTableModel


def _header():
    """每次返回新的 header_list（set_header_list 会往 dict 里写 reg 键）。"""
    return [
        {"label": "Name", "key": "name", "searchable": True},
        {"label": "Age", "key": "age", "editable": True, "display": lambda x, y: "{} 岁".format(x)},
        {"label": "City", "key": "city", "selectable": True, "searchable": True},
    ]


def _source(rows, header=None, use_slice=False, **model_kwargs):
    model = MTableModel(**model_kwargs)
    model.set_header_list(header if header is not None else _header())
    # use_slice=False 拿到全量数据，避免懒加载切片干扰断言
    model.set_data_list(rows, use_slice=use_slice)
    return model


def _proxy(source):
    proxy = MSortFilterModel()
    proxy.setSourceModel(source)
    proxy.set_header_list(source.header_list)
    proxy.set_delayed_filtering(False)  # 同步生效，避免依赖定时器/事件循环
    return proxy


def _first_column_values(model, column=0):
    return [model.data(model.index(row, column), QtCore.Qt.DisplayRole) for row in range(model.rowCount())]


def _age_values(model):
    return [model.data(model.index(row, 1), QtCore.Qt.EditRole) for row in range(model.rowCount())]


# --------------------------------------------------------------------------- #
# EditRole / DisplayRole（回归：编辑往返叠加单位）
# --------------------------------------------------------------------------- #
def test_edit_role_returns_raw_value(qtbot):
    model = _source([{"name": "a", "age": 12, "city": "BJ"}])
    index = model.index(0, 1)
    assert model.data(index, QtCore.Qt.EditRole) == 12
    assert model.data(index, QtCore.Qt.DisplayRole) == "12 岁"


def test_edit_roundtrip_does_not_stack_display_unit(qtbot):
    """回归：EditRole 若返回格式化后的值，setData 回写会让 display 变成 "12 岁 岁"。"""
    model = _source([{"name": "a", "age": 12, "city": "BJ"}])
    index = model.index(0, 1)

    raw = model.data(index, QtCore.Qt.EditRole)
    model.setData(index, raw, QtCore.Qt.EditRole)

    assert model.data(index, QtCore.Qt.DisplayRole) == "12 岁"
    # 重复若干次也不应叠加
    for _ in range(3):
        model.setData(index, model.data(index, QtCore.Qt.EditRole), QtCore.Qt.EditRole)
    assert model.data(index, QtCore.Qt.DisplayRole) == "12 岁"


def test_set_data_updates_value(qtbot):
    model = _source([{"name": "a", "age": 12, "city": "BJ"}])
    index = model.index(0, 1)
    model.setData(index, 30, QtCore.Qt.EditRole)
    assert model.data(index, QtCore.Qt.EditRole) == 30
    assert model.data(index, QtCore.Qt.DisplayRole) == "30 岁"


# --------------------------------------------------------------------------- #
# 组头行（回归：组头可编辑 / 组头染数据色）
# --------------------------------------------------------------------------- #
def _grouped_source():
    rows = [
        {"name": "a", "age": 10, "city": "BJ"},
        {"name": "b", "age": 20, "city": "SH"},
    ]
    tree = group_builder.build_grouped_tree(rows, ["city"])
    return _source(tree)


def test_group_row_is_not_editable(qtbot):
    """回归：组头行曾因沿用列配置而带上 ItemIsEditable，点击会弹出编辑器。"""
    model = _grouped_source()
    for column in range(3):
        flags = model.flags(model.index(0, column))
        assert not (flags & QtCore.Qt.ItemIsEditable), "组头行第 {} 列不应可编辑".format(column)


def test_normal_row_stays_editable(qtbot):
    model = _grouped_source()
    # 组头在第 0 行，叶子在其 children 下（parent=第 0 行第 0 列）
    parent = model.index(0, 0)
    leaf = model.index(0, 1, parent)
    assert model.flags(leaf) & QtCore.Qt.ItemIsEditable


def test_group_row_data_is_none_for_all_roles(qtbot):
    """回归：组头行曾执行数据列 formatter（值恒为 None），导致组头显示下层数据的颜色/图标。"""
    model = _grouped_source()
    roles = [
        QtCore.Qt.DisplayRole,
        QtCore.Qt.EditRole,
        QtCore.Qt.BackgroundRole,
        QtCore.Qt.ForegroundRole,
        QtCore.Qt.FontRole,
        QtCore.Qt.DecorationRole,
        QtCore.Qt.ToolTipRole,
    ]
    for column in range(3):
        index = model.index(0, column)
        for role in roles:
            assert model.data(index, role) is None, "组头行 col={} role={} 应返回 None".format(column, role)


def test_leaf_row_renders_normally(qtbot):
    model = _grouped_source()
    parent = model.index(0, 0)
    leaf = model.index(0, 0, parent)
    assert model.data(leaf, QtCore.Qt.DisplayRole) in ("a", "b")


# --------------------------------------------------------------------------- #
# set_header_list 与预置 reg（回归：预置正则被清空）
# --------------------------------------------------------------------------- #
def test_proxy_set_header_list_keeps_preset_reg(qtbot):
    """回归：MSortFilterModel.set_header_list 曾无条件写入 reg=None，
    把调用方预置的过滤正则清掉（列过滤会静默失效）。"""
    header = _header()
    preset = re.compile("BJ", re.IGNORECASE)
    header[2]["reg"] = preset

    proxy = MSortFilterModel()
    proxy.set_header_list(header)

    assert header[2]["reg"] is preset
    # 预置的 reg 应参与过滤列缓存
    assert any(item is header[2] for _, item in proxy._filter_columns)


def test_proxy_set_header_list_fills_missing_reg_with_none(qtbot):
    header = _header()
    proxy = MSortFilterModel()
    proxy.set_header_list(header)
    assert all("reg" in item for item in header)


# --------------------------------------------------------------------------- #
# 排序
# --------------------------------------------------------------------------- #
def test_sort_by_key_ascending_puts_none_last(qtbot):
    model = _source([
        {"name": "a", "age": None, "city": "BJ"},
        {"name": "b", "age": 30, "city": "BJ"},
        {"name": "c", "age": 10, "city": "BJ"},
    ])
    model.sort_by_key("age", QtCore.Qt.AscendingOrder)
    assert _age_values(model) == [10, 30, None]


def test_sort_by_key_descending(qtbot):
    model = _source([
        {"name": "a", "age": 10, "city": "BJ"},
        {"name": "b", "age": 30, "city": "BJ"},
    ])
    model.sort_by_key("age", QtCore.Qt.DescendingOrder)
    assert _age_values(model) == [30, 10]


def test_sort_mixed_types_does_not_raise(qtbot):
    """排序键三元组保证数值与字符串混排时不抛 TypeError。"""
    model = _source([
        {"name": "a", "age": 10, "city": "BJ"},
        {"name": "b", "age": "unknown", "city": "BJ"},
        {"name": "c", "age": None, "city": "BJ"},
    ])
    model.sort_by_key("age", QtCore.Qt.AscendingOrder)
    # 数值在前，字符串次之，None 最后
    assert _age_values(model) == [10, "unknown", None]


def test_sort_by_column_and_reset(qtbot):
    model = _source([
        {"name": "b", "age": 30, "city": "BJ"},
        {"name": "a", "age": 10, "city": "BJ"},
    ])
    model.sort(0, QtCore.Qt.AscendingOrder)  # 按 name 升序
    assert _first_column_values(model) == ["a", "b"]

    model.sort(-1)  # reset sort
    assert _first_column_values(model) == ["b", "a"]


def test_restore_original_order(qtbot):
    model = _source([
        {"name": "b", "age": 30, "city": "BJ"},
        {"name": "a", "age": 10, "city": "BJ"},
    ])
    model.sort_by_key("name", QtCore.Qt.AscendingOrder)
    assert _first_column_values(model) == ["a", "b"]

    model.restore_original_order()
    assert _first_column_values(model) == ["b", "a"]


# --------------------------------------------------------------------------- #
# 分页
# --------------------------------------------------------------------------- #
def _paged_model(total=25, page_size=10, lazy_chunk_size=100):
    rows = [{"name": "n{}".format(i), "age": i, "city": "BJ"} for i in range(total)]
    model = MTableModel(page_size=page_size, lazy_chunk_size=lazy_chunk_size)
    model.set_header_list(_header())
    model.set_data_list(rows, use_slice=True)
    return model


def test_set_page_first_page(qtbot):
    model = _paged_model()
    model.set_page(1)
    assert model._page_start == 0
    assert model.rowCount() == 10


def test_set_page_last_page(qtbot):
    model = _paged_model()
    model.set_page(3)
    assert model._page_start == 20
    assert model.rowCount() == 5


def test_set_page_below_one_is_clamped(qtbot):
    model = _paged_model()
    model.set_page(0)
    assert model._page_start == 0


def test_set_page_beyond_total_is_clamped(qtbot):
    model = _paged_model()
    model.set_page(999)
    assert model._page_start == 20
    assert model.rowCount() == 5


def test_set_page_with_non_positive_page_size_is_ignored(qtbot):
    model = _paged_model(page_size=0)
    model.set_page(2)
    # page_size<=0 时不进入分页模式
    assert model._paging_active is False


# --------------------------------------------------------------------------- #
# 列过滤 / 搜索
# --------------------------------------------------------------------------- #
def test_filter_attr_pattern_uses_substring_match(qtbot):
    """回归：列过滤使用 re.search（子串匹配），而非全串锚定。"""
    source = _source([
        {"name": "a", "age": 1, "city": "Beijing"},
        {"name": "b", "age": 2, "city": "Shanghai"},
    ])
    proxy = _proxy(source)
    proxy.set_filter_attr_pattern("city", "jing")
    assert proxy.rowCount() == 1


def test_filter_attr_pattern_case_insensitive(qtbot):
    source = _source([{"name": "a", "age": 1, "city": "Beijing"}])
    proxy = _proxy(source)
    proxy.set_filter_attr_pattern("city", "BEIJING")
    assert proxy.rowCount() == 1


def test_filter_attr_pattern_empty_pattern_does_not_filter(qtbot):
    source = _source([
        {"name": "a", "age": 1, "city": "Beijing"},
        {"name": "b", "age": 2, "city": "Shanghai"},
    ])
    proxy = _proxy(source)
    proxy.set_filter_attr_pattern("city", "")
    assert proxy.rowCount() == 2


def test_search_pattern_requires_all_terms(qtbot):
    source = _source([
        {"name": "alpha beta", "age": 1, "city": "BJ"},
        {"name": "alpha", "age": 2, "city": "BJ"},
        {"name": "beta", "age": 3, "city": "BJ"},
    ])
    proxy = _proxy(source)
    proxy.set_search_pattern("alpha beta")
    assert proxy.rowCount() == 1


def test_search_pattern_empty_shows_all(qtbot):
    source = _source([
        {"name": "alpha", "age": 1, "city": "BJ"},
        {"name": "beta", "age": 2, "city": "BJ"},
    ])
    proxy = _proxy(source)
    proxy.set_search_pattern("")
    assert proxy.rowCount() == 2
