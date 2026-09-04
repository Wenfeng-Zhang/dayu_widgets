# Import built-in modules
import contextlib
import signal
import sys

# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets
from Qt.QtSvg import QSvgRenderer


class MCacheDict(object):
    _utils = None
    _dayu_theme = None

    def __init__(self, cls):
        super(MCacheDict, self).__init__()
        self.cls = cls
        self._cache_pix_dict = {}
        self._render = QSvgRenderer()

    @classmethod
    def _get_utils(cls):
        if cls._utils is None:
            from dayu_widgets import utils

            cls._utils = utils
        return cls._utils

    @classmethod
    def _get_dayu_theme(cls):
        if cls._dayu_theme is None:
            from dayu_widgets import dayu_theme

            cls._dayu_theme = dayu_theme
        return cls._dayu_theme

    def _render_svg(self, svg_path, replace_color=None):
        replace_color = replace_color or self._get_dayu_theme().icon_color
        if (self.cls is QtGui.QIcon) and (replace_color is None):
            return QtGui.QIcon(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            data_content = f.read()
            if replace_color is not None:
                data_content = data_content.replace("#555555", replace_color)
            self._render.load(QtCore.QByteArray(data_content.encode()))
            pix = QtGui.QPixmap(128, 128)
            pix.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pix)
            self._render.render(painter)
            painter.end()
            if self.cls is QtGui.QPixmap:
                return pix
            else:
                return self.cls(pix)

    def modify_gray(self, path, gray):
        """
        gray = 'gray'就将图标变成灰色
        """
        if gray != 'gray':
            return self.cls(path)

        origin = QtGui.QPixmap(path).scaled(
            256, 256, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        img = origin.toImage()
        # 用 Qt API 灰度化（O(1) C++ 调用），再把原图的 alpha 通道复制回去：
        # Format_Grayscale8 无 alpha 通道，直接转换会把透明像素（premultiplied RGB≈0）变黑色实心
        try:
            gray_img = img.convertToFormat(QtGui.QImage.Format_Grayscale8)
            alpha_img = img.convertToFormat(QtGui.QImage.Format_Alpha8)
            gray_img.setAlphaChannel(alpha_img)
            img = gray_img
        except AttributeError:
            for i in range(origin.width()):
                for j in range(origin.height()):
                    col = img.pixel(i, j)
                    g_val = QtGui.qGray(col)
                    img.setPixel(i, j, QtGui.qRgb(g_val, g_val, g_val))
        pix = QtGui.QPixmap.fromImage(img)
        qp = QtGui.QPainter(pix)
        pen = QtGui.QPen(QtCore.Qt.red)
        pen.setWidth(2)
        qp.setPen(pen)
        font = QtGui.QFont()
        font.setFamily('Times')
        font.setBold(True)
        font.setPointSize(24)
        qp.setFont(font)
        qp.drawText(10, origin.height() * 0.97, u"标准路径不存在")
        qp.end()

        if self.cls is QtGui.QPixmap:
            return pix
        else:
            return self.cls(pix)

    def __call__(self, path, color=None):
        utils = self._get_utils()
        full_path = utils.get_static_file(path)
        if full_path is None:
            return self.cls()
        key = "{}{}{}".format(full_path.lower(), color or "", self._get_dayu_theme().icon_color if color is None else "")
        pix_map = self._cache_pix_dict.get(key, None)
        if pix_map is None:
            if full_path.endswith("svg"):
                pix_map = self._render_svg(full_path, color)
            else:
                pix_map = self.modify_gray(full_path, color)
            self._cache_pix_dict.update({key: pix_map})
        return pix_map


def get_scale_factor():
    if not QtWidgets.QApplication.instance():
        QtWidgets.QApplication([])
    standard_dpi = 96.0

    # For PySide6
    if hasattr(QtWidgets.QApplication, 'primaryScreen'):
        screen = QtWidgets.QApplication.primaryScreen()
        scale_factor_x = screen.logicalDotsPerInchX() / standard_dpi
        scale_factor_y = screen.logicalDotsPerInchY() / standard_dpi
        return scale_factor_x, scale_factor_y
    # For PySide2
    elif hasattr(QtWidgets.QApplication, 'desktop'):
        scale_factor_x = QtWidgets.QApplication.desktop().logicalDpiX() / standard_dpi
        scale_factor_y = QtWidgets.QApplication.desktop().logicalDpiY() / standard_dpi
        return scale_factor_x, scale_factor_y
    else:
        return 1, 1


@contextlib.contextmanager
def application(*args):
    app = QtWidgets.QApplication.instance()

    if not app:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        app = QtWidgets.QApplication(sys.argv)
        yield app
        app.exec_()
    else:
        # IDE/REPL 下复用已有 app 时也必须进入事件循环，否则窗口 show() 后主线程
        # 立即退出 → 闪退。加防重入标志，避免嵌套调用（如 Maya 宿主已有循环）重复 exec_。
        already_running = app.property("_dayu_application_running")
        if not already_running:
            app.setProperty("_dayu_application_running", True)
            try:
                yield app
                app.exec_()
            finally:
                app.setProperty("_dayu_application_running", False)
        else:
            yield app


MPixmap = MCacheDict(QtGui.QPixmap)
MIcon = MCacheDict(QtGui.QIcon)
