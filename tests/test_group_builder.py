# -*- coding: utf-8 -*-
"""
Test the group_builder module.

group_builder 是纯数据变换（无 UI、无 Qt 依赖），把扁平数据按字段逐层组织成
MTableModel 认识的树形结构。这里覆盖它的取值规则、分组规则与显示文本格式化。
"""

# Import local modules
from dayu_widgets import group_builder


# --------------------------------------------------------------------------- #
# is_group_row
# --------------------------------------------------------------------------- #
def test_is_group_row_true():
    assert group_builder.is_group_row({group_builder.IS_GROUP_KEY: True}) is True


def test_is_group_row_false_for_normal_row():
    assert group_builder.is_group_row({"name": "a"}) is False


def test_is_group_row_false_for_non_dict():
    assert group_builder.is_group_row(None) is False
    assert group_builder.is_group_row("a") is False
    assert group_builder.is_group_row([1, 2]) is False


# --------------------------------------------------------------------------- #
# resolve_field_value
# --------------------------------------------------------------------------- #
def test_resolve_flat_key():
    assert group_builder.resolve_field_value({"season": "S1"}, "season") == "S1"


def test_resolve_missing_key_returns_none():
    assert group_builder.resolve_field_value({"season": "S1"}, "nope") is None


def test_resolve_nested_key():
    assert group_builder.resolve_field_value({"entity": {"season": "S2"}}, "entity.season") == "S2"


def test_resolve_deep_chain():
    row = {"entity": {"CustomEntity07": {"sg_season": "S3"}}}
    assert group_builder.resolve_field_value(row, "entity.CustomEntity07.sg_season") == "S3"


def test_resolve_dict_value_prefers_name():
    assert group_builder.resolve_field_value({"team": {"name": "Lighting", "code": "LGT"}}, "team") == "Lighting"


def test_resolve_dict_value_falls_back_to_code():
    assert group_builder.resolve_field_value({"team": {"code": "LGT"}}, "team") == "LGT"


def test_resolve_list_takes_first_scalar():
    assert group_builder.resolve_field_value({"tags": ["a", "b"]}, "tags") == "a"


def test_resolve_list_of_dict_takes_first_name():
    row = {"tags": [{"name": "first"}, {"name": "second"}]}
    assert group_builder.resolve_field_value(row, "tags") == "first"


def test_resolve_empty_list_returns_empty_string():
    assert group_builder.resolve_field_value({"tags": []}, "tags") == ""


def test_resolve_non_dict_row_returns_none():
    assert group_builder.resolve_field_value(None, "season") is None
    assert group_builder.resolve_field_value("x", "season") is None


# --------------------------------------------------------------------------- #
# build_grouped_tree
# --------------------------------------------------------------------------- #
def test_build_without_group_fields_returns_original_list():
    rows = [{"a": 1}, {"a": 2}]
    assert group_builder.build_grouped_tree(rows, []) == rows


def test_build_skips_falsy_group_fields():
    rows = [{"name": "a", "sex": "M"}]
    assert group_builder.build_grouped_tree(rows, ["", None]) == rows


def test_build_single_level():
    rows = [
        {"name": "a", "sex": "M"},
        {"name": "b", "sex": "F"},
        {"name": "c", "sex": "M"},
    ]
    tree = group_builder.build_grouped_tree(rows, ["sex"])

    assert len(tree) == 2
    assert all(group_builder.is_group_row(node) for node in tree)
    # 组名按字符串排序
    assert [n[group_builder.GROUP_TEXT_KEY] for n in tree] == ["F", "M"]

    counts = {n[group_builder.GROUP_TEXT_KEY]: n[group_builder.GROUP_COUNT_KEY] for n in tree}
    assert counts == {"F": 1, "M": 2}

    group_m = next(n for n in tree if n[group_builder.GROUP_TEXT_KEY] == "M")
    assert group_m[group_builder.GROUP_LEVEL_KEY] == 0
    assert group_m[group_builder.GROUP_VALUE_KEY] == "M"
    assert len(group_m["children"]) == 2
    # 叶子节点是原始行
    assert group_m["children"][0]["sex"] == "M"


def test_build_nested_levels():
    rows = [
        {"name": "a", "sex": "M", "city": "BJ"},
        {"name": "b", "sex": "M", "city": "SH"},
        {"name": "c", "sex": "F", "city": "BJ"},
    ]
    tree = group_builder.build_grouped_tree(rows, ["sex", "city"])

    assert len(tree) == 2
    group_m = next(n for n in tree if n[group_builder.GROUP_TEXT_KEY] == "M")
    assert group_m[group_builder.GROUP_LEVEL_KEY] == 0
    # 第二层依旧是组头节点
    assert all(group_builder.is_group_row(child) for child in group_m["children"])
    assert all(child[group_builder.GROUP_LEVEL_KEY] == 1 for child in group_m["children"])
    assert sorted(c[group_builder.GROUP_TEXT_KEY] for c in group_m["children"]) == ["BJ", "SH"]


def test_build_none_value_becomes_empty_label():
    rows = [{"name": "a", "city": None}, {"name": "b", "city": "BJ"}]
    tree = group_builder.build_grouped_tree(rows, ["city"])
    assert "(空)" in [n[group_builder.GROUP_TEXT_KEY] for n in tree]


def test_build_uses_display_map_for_label():
    rows = [{"name": "a", "duration": 1440}]
    display_map = {"duration": lambda value, row: "{} 天".format(value / 480.0)}
    tree = group_builder.build_grouped_tree(rows, ["duration"], display_map)
    assert tree[0][group_builder.GROUP_TEXT_KEY] == "3.0 天"


def test_build_display_map_exception_falls_back_to_raw_value():
    def boom(value, row):
        raise ValueError("boom")

    rows = [{"name": "a", "d": 5}]
    tree = group_builder.build_grouped_tree(rows, ["d"], {"d": boom})
    assert tree[0][group_builder.GROUP_TEXT_KEY] == "5"


def test_build_normalizes_whitespace_in_label():
    rows = [{"name": "a", "note": "hello\n\tworld"}]
    tree = group_builder.build_grouped_tree(rows, ["note"])
    assert tree[0][group_builder.GROUP_TEXT_KEY] == "hello world"


def test_build_count_is_leaf_count_not_node_count():
    rows = [{"name": "a", "sex": "M", "city": "BJ"}, {"name": "b", "sex": "M", "city": "SH"}]
    tree = group_builder.build_grouped_tree(rows, ["sex", "city"])
    # 顶层组计数应为叶子总数，而不是子组个数
    assert tree[0][group_builder.GROUP_COUNT_KEY] == 2


def test_build_empty_and_none_input():
    assert group_builder.build_grouped_tree([], ["sex"]) == []
    assert group_builder.build_grouped_tree(None, ["sex"]) == []
