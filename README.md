# dayu_widgets

<p align="center">
<a href="https://img.shields.io/pypi/pyversions/dayu_widgets">
<img src="https://img.shields.io/pypi/pyversions/dayu_widgets" alt="python version"></a>
<a href="https://badge.fury.io/py/dayu_widgets">
<img src="https://img.shields.io/pypi/v/dayu_widgets?color=green" alt="PyPI version"></a>
<img src="https://img.shields.io/pypi/dw/dayu_widgets" alt="Downloads Status">
<img src="https://img.shields.io/pypi/l/dayu_widgets" alt="License">
<img src="https://img.shields.io/pypi/format/dayu_widgets" alt="pypi format">
<img src="https://img.shields.io/badge/Maintained%3F-yes-green.svg" alt="Maintenance"></a>
<a href="https://context7.com/phenom-films/dayu_widgets">
<img src="https://img.shields.io/badge/Context7-Enabled-blue" alt="Context7 Enabled"></a>

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-3-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
</p>

<!-- ================= 以下为本 fork 新增内容（相对上游 v1.1.1） ================= -->

## 📌 本 Fork 更新说明

> 本仓库基于上游 [dayu_widgets](https://github.com/phenom-films/dayu_widgets) fork，版本升至 **1.2.0**（Qt 抽象层由 `qtpy` 切换为 `Qt.py`，不再兼容 Python 2）。以下为相对上游 v1.1.1 的主要更新，完整变更见 [CHANGELOG.md](CHANGELOG.md)。

### 模型层（item_model.py）
- `MTableModel` 支持生成器/迭代器数据源，`fetchMore` 逐块消费，可承载超大数据集
- 新增显式分页 `set_page()` 与页内懒加载，配合 `MItemViewFullSet` 实现"分页 + 懒加载 + 过滤后重建分页"（见 `examples/tree_view_paging_example.py`）
- 重写排序：Python 层整体排序、`None` 恒置尾部，`restore_original_order()` 可恢复插入顺序
- `MSortFilterModel` 新增 300ms 延迟过滤（防抖）、批量过滤接口、过滤结果缓存及 `filter_finished`/`sort_finished` 信号；树形过滤支持"子项命中则保留父项"

### 视图层（item_view.py / header_view.py）
- `MTreeView.expandAll` 先 `load_all_data()` 再批量展开，规避 PySide6 逐节点 `fetchMore` 卡顿
- `MHeaderView` 上下文菜单新增 **Reset Sort**；修复排序指示器首次点击不生效、EditRole 为 `None` 时委托崩溃等问题

### 组件增强与修复
- `MSplitter`：双击 handle 均分，handle 新增折叠/展开箭头按钮
- `MPage`：修复首次翻页不触发与页码越界问题
- `MSequenceFile`：新增 `file_label`/`sequence_check_box` 属性并加入公共导出
- `browser.py` 新增 `FileButton`：支持拖入目录递归收集匹配文件

### 基础设施
- 新增 `CUSTOM_STATIC_FOLDERS` 机制，可注入自定义静态资源目录
- `main.qss` 主题样式大量更新（约 +345 行）：新增 wizard 步骤条（`QLabel#wizard-step`）、`QToolButton[taobao=true]`、登录/搜索/加号按钮、QComboBox、QGroupBox 等选择器
- `utils.py`：修复 `from_list_to_nested_dict` 丢失子树、`add_settings` 增加控件存活检查与 `unbind`

### 新增示例
- `examples/delegate_button_example2.py` — 表格内按钮委托
- `examples/tree_view_multi_level_example.py` — 多层树懒加载
- `examples/tree_view_50000_example.py` — 5 万行压力测试
- `examples/tree_view_paging_example.py` — 分页 + 页内懒加载 + 过滤重建分页
- `examples/grouped_grid_view_example.py` — 分组表格 / 分组大图示例

### 新增控件：分组表格 / 分组大图
- `MGroupedGridView`：按一个或多个字段逐层分组的表格 + 大图组合控件（分组字段可多选、搜索、展开/折叠）
- `GroupedBigView`：按组分块的缩略图流（只显示有图行，组头计数随搜索实时更新）
- `group_builder`：纯数据变换工具，把扁平数据组织成 `MTableModel` 认识的树形结构

### 工程标准化与本轮修复
- **Qt.py 升级到 2.0.5**（`pyproject.toml`/`setup.cfg`/`poetry.lock` 同步），修复旧约束 `^1.3.8` 锁定 1.4.8 导致的 `QRegularExpression` 属性缺失
- **正则过滤还原为标准库 `re`**：跨 Qt5/Qt6 零耦合；真实 GUI 场景实测 `re` 比 Qt 正则快约 1.15x（裸循环快 4-6x，端到端差距被 model.data()/信号稀释）
- 补 `setup.py`、`.editorconfig`、`.gitattributes`（统一 LF、跨 IDE 缩进），`pip install -e .` 可用
- 修复 `application()` 复用已有 app 时不进事件循环导致的启动闪退（含防重入）
- 修复 `grouped_grid_view` 在 PySide6 下的段错误（delegate 里 `setRenderHint(Antialiasing)` + `QPolygon` 改为 `QPainterPath`）
- 修复 PySide6 下 `disconnect` 的 `RuntimeWarning`（新增 `utils.safe_disconnect`）
- 依赖约束修正：`PySide2 <3.11`、`PySide6 >=6.4.2,<6.7`、补 `dayu_path`
- 清理 52 个 example 的 `from __future__` 残留、修正 version 对齐 1.2.0

<!-- ================= 以上为本 fork 新增内容 ================= -->

> **AI Assistant Integration**: This project is integrated with [Context7](https://context7.com/phenom-films/dayu_widgets), allowing AI assistants to access up-to-date documentation and examples. Try prompts like: `帮我创建一个dayu_widgets的进度条， use context7`


Components for PySide

主要参考了 [AntDesign](https://ant.design/) 组件库，其他参考了 [iView](https://www.iviewui.com/) 组件库，微信基础组件。

更多在此基础上的组件插件：

* [dayu_widgets_tag](https://github.com/muyr/dayu_widgets_tag):  [中文](https://muyr.github.io/dayu_widgets_tag/#/zh-cn/) | [EN](https://muyr.github.io/dayu_widgets_tag/#/)
* [dayu_widgets_log](https://github.com/muyr/dayu_widgets_log):  [中文](https://muyr.github.io/dayu_widgets_log/#/zh-cn/) | [EN](https://muyr.github.io/dayu_widgets_log/#/)
* [dayu_widgets_overlay](https://github.com/FXTD-ODYSSEY/dayu_widgets_overlay)

提供**亮色(light)** 和 **暗色(dark)** 两种主题，每种主题可以设置主题颜色。
以下截图以：

* 亮色 #1890ff
* 暗色 #fa8c16

## General


### MPushButton(<- QPushButton)
![pageres](screenshots/push_button_light.png)![pageres](screenshots/push_button_dark.png)

### MLabel (<- QLabel)
![pageres](screenshots/label_light.png)![pageres](screenshots/label_dark.png)

### MLoading (<- QWidget)
![pageres](screenshots/loading_light.gif)![pageres](screenshots/loading_dark.gif)

### MToolButton (<- QToolButton)
![pageres](screenshots/tool_button_light.png)![pageres](screenshots/tool_button_dark.png)

## Navigation


### MBreadcrumb (<- QWidget)
![pageres](screenshots/breadcrumb_light.gif)![pageres](screenshots/breadcrumb_dark.gif)

### MMenuTabWidget (<- QWidget)
![pageres](screenshots/menu_tab_widget_light.png)![pageres](screenshots/menu_tab_widget_dark.png)

### MPage (<- QWidget)
![pageres](screenshots/page_light.png)![pageres](screenshots/page_dark.png)


## Data Entry


### MCheckBox <- QCheckBox
![pageres](screenshots/check_box_light.png)![pageres](screenshots/check_box_dark.png)

### MClickBrowserFilePushButton <- MPushButton
### MClickBrowserFileToolButton <- MToolButton
### MClickBrowserFolderPushButton <- MPushButton
### MClickBrowserFolderToolButton <- MToolButton
### MDragFileButton <- MToolButton
### MDragFolderButton <- MToolButton
![pageres](screenshots/browser_light.png)![pageres](screenshots/browser_dark.png)

### MLineEdit <- QLineEdit
![pageres](screenshots/line_edit_light.png)![pageres](screenshots/line_edit_dark.png)

### MRadioButton <- QRadioButton
![pageres](screenshots/radio_button_light.png)![pageres](screenshots/radio_button_dark.png)

### MSwitch <- QRadioButton
![pageres](screenshots/switch_light.png)![pageres](screenshots/switch_dark.png)

### MSilder <- QSlider
![pageres](screenshots/slider_light.png)![pageres](screenshots/slider_dark.png)

### MSpinBox <- QSpinBox
### MDoubleSpinBox  <- QDoubleSpinBox
### MDateTimeEdit <- QDateTimeEdit
### MDateEdit <- QDateEdit
### MTimeEdit <- QTimeEdit
![pageres](screenshots/spin_box_light.png)![pageres](screenshots/spin_box_dark.png)


## Data Display


### MAvatar <- QLabel
![pageres](screenshots/avatar_light.png)![pageres](screenshots/avatar_dark.png)

### MBadge <- QWidget
![pageres](screenshots/badge_light.png)![pageres](screenshots/badge_dark.png)


### MCarousel <- QGraphicsView
![pageres](screenshots/carousel_light.gif)![pageres](screenshots/carousel_dark.gif)

### MCard <- QWidget
![pageres](screenshots/card_light.png)![pageres](screenshots/card_dark.png)

### MCollapse <- QWidget
![pageres](screenshots/collapse_light.gif)![pageres](screenshots/collapse_dark.gif)

### MLineTabWidget <- QWidget
![pageres](screenshots/line_tab_widget_light.gif)![pageres](screenshots/line_tab_widget_dark.gif)

### MTag <- QLabel
### MCheckableTag <- QCheckBox
### MNewTag <- QWidget
![pageres](screenshots/tag_light.png)![pageres](screenshots/tag_dark.png)


## Feedback


### MAlert <- QWidget
![pageres](screenshots/alert_light.png)![pageres](screenshots/alert_dark.png)

### MDrawer <- QWidget
![pageres](screenshots/drawer_light.gif)![pageres](screenshots/drawer_dark.gif)

### MMessage <- QWidget
![pageres](screenshots/message_light.gif)![pageres](screenshots/message_dark.gif)

### MProgressBar <- QProgressBar
![pageres](screenshots/progressbar_light.gif)![pageres](screenshots/progressbar_dark.gif)

### MProgressCircle <- QProgressBar
![pageres](screenshots/progress_circle_light.png)![pageres](screenshots/progress_circle_dark.png)

### MToast <- QWidget
![pageres](screenshots/toast_light.gif)![pageres](screenshots/toast_dark.gif)

## Other

### MDivider <- QWidget
![pageres](screenshots/divider_light.png)![pageres](screenshots/divider_dark.png)


# 使用方法

## 安装

```shell
pip install dayu_widgets
```

## 运行示例程序

安装后，可以通过以下命令直接运行示例程序。注意，运行示例程序需要 Qt 环境（PySide2 或 PySide6）：

```shell
# 使用 Python 模块方式运行（需要先安装 PySide2 或 PySide6）
python -m dayu_widgets

# 使用 uvx 命令行工具运行（推荐方式，自动处理依赖）
uvx --python 3.10 --with pyside2 dayu_widgets
```

> **注意**：dayu_widgets 是一个 Qt 界面库，运行示例程序需要 Qt 环境。使用 `uvx` 命令时可以通过 `--with pyside2` 参数自动处理 Qt 依赖。

# 如何贡献代码

## 安装poetry
```shell
pip install poetry
```

## 安装依赖
```shell
poetry install
```

## 运行单元测试
```shell
poetry run pytest
```

## 运行 black检查
```shell
poetry run black dayu_widgets
```

## 运行isort
```shell
poetry run isort dayu_widgets
```

## 提交代码
```shell
poetry run cz commit
```

## Context7 Integration

This project includes a `llms.txt` file that provides code examples and documentation for AI assistants and LLMs through [Context7](https://context7.com/). The file is automatically generated from the examples in the `examples/` directory.

To manually generate the `llms.txt` file, run:

```shell
python scripts/generate_llms_txt.py
```

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/muyr"><img src="https://avatars.githubusercontent.com/u/1860334?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Yanru Mu</b></sub></a><br /><a href="https://github.com/phenom-films/dayu_widgets/commits?q=author%3Yanru Mu" itle="Code">💻</a></td>
    <td align="center"><a href="https://github.com/loonghao"><img src="https://avatars1.githubusercontent.com/u/13111745?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Hal</b></sub></a><br /><a href="https://github.com/phenom-films/dayu_widgets/commits?author=loonghao" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/FXTD-ODYSSEY"><img src="https://avatars.githubusercontent.com/u/40897360?v=4?s=100" width="100px;" alt=""/><br /><sub><b>FXTD-ODYSSEY</b></sub></a><br /><a href="https://github.com/phenom-films/dayu_widgets/commits?author=FXTD-ODYSSEY" title="Code">💻</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
