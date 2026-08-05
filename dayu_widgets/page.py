"""MPage"""

# Import built-in modules
import functools

# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets import utils
from dayu_widgets.combo_box import MComboBox
from dayu_widgets.field_mixin import MFieldMixin
from dayu_widgets.label import MLabel
from dayu_widgets.menu import MMenu
from dayu_widgets.spin_box import MSpinBox
from dayu_widgets.tool_button import MToolButton


class MPage(QtWidgets.QWidget, MFieldMixin):
    """
    MPage
    A long list can be divided into several pages by MPage,
    and only one page will be loaded at a time.
    """

    sig_page_changed = QtCore.Signal(int, int)

    def __init__(self, parent=None):
        super(MPage, self).__init__(parent)
        self.register_field("page_size_selected", 25)
        self.register_field(
            "page_size_list",
            [
                {"label": "25 - Fastest", "value": 25},
                {"label": "50 - Fast", "value": 50},
                {"label": "75 - Medium", "value": 75},
                {"label": "100 - Slow", "value": 100},
            ],
        )
        self.register_field("total", 0)
        # 与 _current_page_spin_box.setMinimum(1) 保持一致，
        # 否则 field(0) 与 spinbox(1) 不一致会导致首次翻页不触发 valueChanged
        self.register_field("current_page", 1)
        self.register_field(
            "total_page",
            lambda: max(
                1,
                utils.get_total_page(self.field("total"), self.field("page_size_selected")),
            ),
        )
        self.register_field("total_page_text", lambda: str(self.field("total_page")))
        self.register_field(
            "display_text",
            lambda: utils.get_page_display_string(
                self.field("current_page"),
                self.field("page_size_selected"),
                self.field("total"),
            ),
        )
        self.register_field("can_pre", lambda: self.field("current_page") > 1)
        self.register_field("can_next", lambda: self.field("current_page") < self.field("total_page"))
        page_setting_menu = MMenu(parent=self)
        self._display_label = MLabel()
        self._display_label.setAlignment(QtCore.Qt.AlignCenter)
        self._change_page_size_button = MComboBox().small()
        self._change_page_size_button.set_menu(page_setting_menu)
        self._change_page_size_button.set_formatter(lambda x: "{} per page".format(x))

        self._pre_button = MToolButton().icon_only().svg("left_fill.svg").small()
        self._pre_button.clicked.connect(functools.partial(self._slot_change_current_page, -1))
        self._next_button = MToolButton().small().icon_only().svg("right_fill.svg")
        self._next_button.clicked.connect(functools.partial(self._slot_change_current_page, 1))
        self._current_page_spin_box = MSpinBox()
        self._current_page_spin_box.setMinimum(1)
        self._current_page_spin_box.set_dayu_size(dayu_theme.small)
        self._current_page_spin_box.valueChanged.connect(self._emit_page_changed)
        self._total_page_label = MLabel()

        self.bind("page_size_list", page_setting_menu, "data")
        self.bind("page_size_selected", page_setting_menu, "value", signal="sig_value_changed")
        self.bind(
            "page_size_selected",
            self._change_page_size_button,
            "value",
            signal="sig_value_changed",
        )
        self.bind("current_page", self._current_page_spin_box, "value", signal="valueChanged")
        self.bind("total_page", self._current_page_spin_box, "maximum")
        self.bind("total_page_text", self._total_page_label, "dayu_text")
        self.bind("display_text", self._display_label, "dayu_text")
        self.bind("can_pre", self._pre_button, "enabled")
        self.bind("can_next", self._next_button, "enabled")

        self._change_page_size_button.sig_value_changed.connect(self._emit_page_changed)

        main_lay = QtWidgets.QHBoxLayout()
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(2)
        main_lay.addStretch()
        main_lay.addWidget(self._display_label)
        main_lay.addStretch()
        main_lay.addWidget(MLabel("|").secondary())
        main_lay.addWidget(self._change_page_size_button)
        main_lay.addWidget(MLabel("|").secondary())
        main_lay.addWidget(self._pre_button)
        main_lay.addWidget(MLabel("Page"))
        main_lay.addWidget(self._current_page_spin_box)
        main_lay.addWidget(MLabel("/"))
        main_lay.addWidget(self._total_page_label)
        main_lay.addWidget(self._next_button)
        self.setLayout(main_lay)

    def set_total(self, value):
        """Set page component total count."""
        self.set_field("total", value)
        # 页码越界时钳制到最后一页（而非无条件回第 1 页），避免翻页后被刷新打断
        total_page = self.field("total_page")
        if self.field("current_page") > total_page:
            self.set_field("current_page", max(1, total_page))

    def _slot_change_current_page(self, offset):
        # 通过 set_field 触发 spinbox valueChanged -> _emit_page_changed，避免重复发射
        self.set_field("current_page", self.field("current_page") + offset)

    def set_page_config(self, data_list):
        """Set page component per page settings."""
        self.set_field(
            "page_size_list",
            [{"label": str(data), "value": data} if isinstance(data, int) else data for data in data_list],
        )

    def _emit_page_changed(self):
        # 防止 set_field -> valueChanged -> _emit_page_changed 的再入导致信号重复发射
        if getattr(self, "_emitting_page_changed", False):
            return
        self._emitting_page_changed = True
        try:
            # 以 spinbox 实际值为准：用户手动改 spinbox 时 field 可能尚未同步
            # （valueChanged 先连接 _emit_page_changed，后连接 bind 的 _slot_changed_from_user）
            current_page = self._current_page_spin_box.value()
            self.set_field("current_page", current_page)
            total_page = self.field("total_page")
            if current_page > total_page:
                # 钳制页码到合法范围（例如切换 page_size 后总页数变小）
                current_page = max(1, total_page)
                self.set_field("current_page", current_page)
            self.sig_page_changed.emit(self.field("page_size_selected"), current_page)
        finally:
            self._emitting_page_changed = False
