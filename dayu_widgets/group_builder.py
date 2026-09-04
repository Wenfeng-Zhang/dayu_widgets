# -*- coding: utf-8 -*-
"""分组数据构建器（无 UI，纯数据变换）。

把扁平的 data_list 按一个或多个字段【逐层嵌套】组织成 dayu MTableModel 认识的
树形结构（每个节点是 dict，子节点放在 "children" 键里）。这样可以直接喂给
MTableModel + MTreeView，自动复用原表格的全部渲染（缩略图/状态色/字体等）。

组头节点约定：
    - 标记键 IS_GROUP_KEY = True；
    - GROUP_TEXT_KEY 存组名纯文本（已经过该列 display 格式化，不含计数）；
      组名由 delegate（表格）/组头控件（大图）直接绘制，计数为动态值（随搜索/
      折叠实时统计），故不在构建期写死"分组值 (数量)"。
    - 持有 "children"（下一层组头 或 叶子数据行）。
"""

IS_GROUP_KEY = "_is_group_row"        # 标记该 dict 是组头
GROUP_LEVEL_KEY = "_group_level"      # 组头所在层级(0=最外层)
GROUP_VALUE_KEY = "_group_value"      # 组的原始值（未加计数、未格式化）
GROUP_COUNT_KEY = "_group_count"      # 该组下的叶子数据总数
GROUP_TEXT_KEY = "_group_text"        # 组名纯文本（已格式化，不含计数）


def resolve_field_value(row_dict, field_key):
    """取某字段值，支持扁平 key 和 'entity.<Type>.<field>' 深链，dict 值取 name/code。"""
    if not isinstance(row_dict, dict):
        return None
    val = row_dict.get(field_key)
    if val is None and "." in field_key:
        parts = field_key.split(".")
        cur = row_dict
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                cur = None
                break
        if cur is not None:
            val = cur
        else:
            ent = row_dict.get("entity")
            if isinstance(ent, dict):
                val = ent.get(parts[-1])
    if isinstance(val, dict):
        val = val.get("name") or val.get("code") or val.get("id") or ""
    if isinstance(val, (list, tuple)):
        if val:
            first = val[0]
            if isinstance(first, dict):
                return first.get("name") or first.get("code") or ""
            return str(first)
        return ""
    return val


def build_grouped_tree(data_list, group_fields, field_display_map=None):
    """按 group_fields 逐层分组，返回可直接 set_data_list 的节点列表。

    data_list:         扁平原始行 [row_dict, ...]
    group_fields:      分组字段 key 列表；空 → 直接返回原 data_list（不分组）
    field_display_map: {field_key: display_func}，用于把组的原始值格式化成显示文本
                       （如 CP制作时长 1440 → "3.0 天"）。display_func(value, row) -> str。
    """
    data_list = list(data_list or [])
    group_fields = [f for f in (group_fields or []) if f]
    if not group_fields:
        return data_list
    return _group_recursive(data_list, group_fields, 0, field_display_map or {})


def _normalize_label(text):
    """把组名里的换行/制表符等空白规整成单个空格（仅影响分组名显示，不动源数据）。"""
    if text in (None, ""):
        return text
    if not isinstance(text, str):
        text = str(text)
    return u" ".join(text.split())


def _format_group_value(raw_value, sample_row, field, field_display_map):
    """用该列的 display 函数格式化组值；无 display 则返回原值字符串。"""
    display_func = field_display_map.get(field)
    if display_func is not None:
        try:
            text = display_func(raw_value, sample_row)
            if text not in (None, ""):
                return _normalize_label(text)
        except Exception:
            pass
    if raw_value in (None, ""):
        return u"(空)"
    return _normalize_label(raw_value)


def _group_recursive(rows, group_fields, level, field_display_map):
    field = group_fields[level]
    buckets = {}
    order = []
    sample = {}
    for row in rows:
        val = resolve_field_value(row, field)
        key = val if val not in (None, "") else u"(空)"
        key_str = key if isinstance(key, str) else str(key)
        if key_str not in buckets:
            buckets[key_str] = []
            order.append(key_str)
            sample[key_str] = (val, row)   # 记录原始值 + 样本行，供 display 格式化
        buckets[key_str].append(row)

    nodes = []
    for key_str in sorted(order):
        bucket_rows = buckets[key_str]
        leaf_count = len(bucket_rows)
        raw_value, sample_row = sample[key_str]
        display_text = _format_group_value(
            raw_value, sample_row, field, field_display_map)
        group_node = {
            IS_GROUP_KEY: True,
            GROUP_LEVEL_KEY: level,
            GROUP_VALUE_KEY: key_str,
            GROUP_COUNT_KEY: leaf_count,
            GROUP_TEXT_KEY: display_text,
        }
        if level + 1 < len(group_fields):
            group_node["children"] = _group_recursive(
                bucket_rows, group_fields, level + 1, field_display_map)
        else:
            group_node["children"] = list(bucket_rows)
        nodes.append(group_node)
    return nodes


def is_group_row(row_dict):
    return isinstance(row_dict, dict) and row_dict.get(IS_GROUP_KEY) is True
