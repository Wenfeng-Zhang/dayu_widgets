## v1.2.1 (2025-09-05)

### Fix

- 修复 grouped grid view 组头行渲染错误：组头行现在只由第 0 列自绘整行，其它列不再叠加下层数据的人像图标/颜色/编辑控件
- 修复 display formatter 在 EditRole 被重复应用导致编辑往返叠加单位（"12 岁" → "12 岁 岁"）：EditRole 返回原始值
- 修复组头行触发 editable/selectable 列编辑器和数据 role formatter：组件 data() 对组头行短路、flags() 去掉组头 ItemIsEditable
- 修复 examples 中 4 个文件（_mock_data.py、delegate_button_example.py、delegate_button_example2.py、tree_view_multi_level_example.py）icon formatter 对 None 值的崩溃
- 删除 main.qss 中 128 行冗余选择器（wizard/login/MColumnView 等未使用样式）
- 分组缩进 22→10、最后一列撑满、删除无用 `_apply_span` 空遍历

## v1.2.0 (2025-07-31)

### BREAKING CHANGE

- Switch from `qtpy` to `Qt.py` as Qt abstraction layer
- Drop Python 2 compatibility by removing `__future__` imports

### Feat

- Add `MSequenceFile` widget to public API exports
- Add `file_label` and `sequence_check_box` properties to `MSequenceFile`
- Add `modify_gray()` method for gray icon fallback with text overlay
- Add lazy import pattern (`_get_utils`, `_get_dayu_theme`) to break circular dependencies
- Use Qt native grayscale conversion for image processing
- Major `item_model.py` and `browser.py` refactoring and improvements
- Add extensive QSS style updates to `main.qss`

### Refactor

- Migrate examples from `qtpy` to `Qt` module imports
- Remove `__future__` imports across all source files

### Fix (2025-08-29)

- Fix `QRegularExpression` AttributeError on PySide2 by reverting regex to stdlib `re` (Qt5/Qt6 agnostic)
- Upgrade `Qt.py` from `^1.3.8` to `>=2.0.5` in `pyproject.toml`/`setup.cfg`/`poetry.lock`
- Fix `application()` not entering event loop when reusing an existing QApplication (startup flash-crash)
- Fix PySide6 segfault in `grouped_grid_view` (delegate `setRenderHint(Antialiasing)` + `QPolygon` → `QPainterPath`)
- Add `utils.safe_disconnect` to silence PySide6 `RuntimeWarning` on `disconnect`
- Fix `MAlert` parent-less window flash in `table_view_example`
- Constrain `PySide2 <3.11`, `PySide6 >=6.4.2,<6.7`, add `dayu_path` dependency
- Add `MGroupedGridView` / `GroupedBigView` / `group_builder` grouped table & big view widgets

## v1.1.1 (2025-07-28)

### Fix

- correct malformed JSON in .all-contributorsrc and add CI permissions

## v1.1.0 (2025-07-24)

### Feat

- update cr

## v1.0.0 (2025-07-24)

### BREAKING CHANGE

- pytest-qt 4.5.0 dropped support for PySide2

### Feat

- Apply successful repository's pytest-qt version strategy
- Completely adopt reference repository strategy
- Support for PySide6

### Fix

- Use pytest-qt<4.5.0 to maintain PySide2 support
- Add Python version compatibility check for PySide2
- Remove qt_api = auto from pytest.ini
- Pin pytest-qt version to support PySide2
- Add setup.cfg to resolve package discovery issues

### Refactor

- Adopt reference repository strategy for pytest-qt

## v0.15.0 (2025-04-27)

### Feat

- add script to generate llms.txt for Context7 integration

## v0.14.1 (2025-04-25)

### Fix

- **deps**: update dependency qt.py to v1.4.4

## v0.14.0 (2025-04-25)

### Feat

- add command line entry point for running demo
- add command line entry point for running demo

### Fix

- use app variable in __main__.py to avoid unused variable warning

## v0.13.15 (2024-10-28)

### Fix

- set min-height qss for vertical handle(when to show thousands data, handle too small)

## v0.13.14 (2024-08-03)

### Fix

- fix MLabel

## v0.13.13 (2024-06-21)

### Fix

- change size in qss to theme variable

## v0.13.12 (2024-06-21)

### Fix

- MToast show wrong position when its parent window in DCC

## v0.13.11 (2024-06-21)

### Fix

- MMessage show wrong position when its parent window in DCC

## v0.13.10 (2024-06-21)

### Fix

- QSize need int, convert float to int (#94)

## v0.13.9 (2024-06-21)

### Fix

- cursor mixin when lose focus, restore to arrow cursor #81 (#93)

## v0.13.8 (2024-06-21)

### Fix

- remove fixed color and useless code in qss file

## v0.13.7 (2024-06-21)

### Fix

- Fix compatible menu multi-select and single value

## v0.13.6 (2024-06-21)

### Fix

- tab widget example showed in demo

## v0.13.5 (2024-06-14)

### Fix

- 修复偶发的找不到Qt绑定的bug

## v0.13.4 (2024-06-13)

### Fix

- update ci publish pypi config to use trusted publisher

## v0.13.3 (2024-06-12)

### Fix

- period

## v0.13.2 (2024-06-12)

### Fix

- MMenu multi select no a correct action

## v0.13.1 (2023-09-26)

### Fix

- fix header view context menu Select Invert

## v0.13.0 (2023-09-25)

### Feat

- #66 support python 3.10

## v0.12.2 (2023-08-17)

### Fix

- #67 fix MToolButon set_dayu_size use a custom value, not work

## v0.12.1 (2023-08-17)

### Fix

- flow layout delete item; add clear method

## v0.12.0 (2023-08-17)

### Feat

- add theme var for big view scale #65

## v0.11.6 (2023-03-07)

### Fix

- compat with PyQt5

## v0.11.5 (2022-07-22)

### Fix

- **MItemView**: fix header view order(sort) setting

## v0.11.4 (2022-07-22)

### Fix

- **MItemViewSet-MItemViewFullSet**: fix headerView state restore

## v0.11.3 (2022-07-20)

### Fix

- **MTheme**: fix MTheme.deco function

## v0.11.2 (2022-07-19)

### Fix

- **MPage**: fix MPage sig_page_changed bug

## v0.11.1 (2022-07-19)

### Fix

- fix MLineEdit delay signal not work when user use Chinese input method

## v0.11.0 (2021-12-28)

### Feat

- **MComboBox**: using MCompleter

### Refactor

- **MMenu**: clean up menu code
- fix example application

## v0.10.1 (2021-12-15)

### Refactor

- **examples**: use application function to launch example

## v0.10.0 (2021-12-14)

### Feat

- **MSplitter**: add animatable feature

## v0.9.1 (2021-12-14)

### Fix

- **MPopup**: fix PyQt5 setMask bug & clean code

## v0.9.0 (2021-12-08)

### Feat

- add MCompleter and MSplitter widget

## v0.8.0 (2021-12-06)

### Fix

- deploy fialed
- add __all__ import
- delegate example rename for demo.py
- clean combox search code
- chinese input support

### Feat

- edit read_settings and write_settings
- edit read_settings and write_settings
- add search and scroll for MMenu
- add MPopup widget
- add delegate example
- add searchable combo box
