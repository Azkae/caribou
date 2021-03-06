import sys
import time
import os
import requests
import json
import traceback
from requests.models import PreparedRequest
from pygments.token import Name, String, Number, Keyword
from pygments.lexers import JsonLexer
from PySide2.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QApplication,
    QVBoxLayout, QHBoxLayout, QMainWindow, QWidget,
    QTextEdit, QPlainTextEdit, QFrame, QComboBox, QScrollArea,
    QShortcut, QFileDialog, QAction, QMessageBox
)
from PySide2.QtCore import Signal, QThreadPool, QRunnable, Slot, QObject, Qt, QFileSystemWatcher
from PySide2.QtGui import (
    QIcon, QFont, QTextCharFormat, QSyntaxHighlighter, QColor,
    QKeySequence, QTextDocument, QTextCursor, QPalette, QFontMetrics
)
from .models import Route, Choice, List, TextField
from .loader import load_file
from .storage import (
    save_parameter, load_parameter, get_parameter_values_for_route,
    load_request_result, save_request_result, MissingParameter,
    persist_storage, load_storage, load_setting, save_setting
)
from .exceptions import CaribouException

CURRENT_DIR = os.path.dirname(__file__)

FONT = QFont('Fira Mono')
FONT_ROUTE = QFont('Fira Mono', 11)
TEXT_FONT = QFont('Fira Mono')


class RouteButton(QPushButton):
    def __init__(self, route):
        super().__init__(route.raw_display_name)

        self.setStyleSheet("color:rgba(0,0,0,0)")

        self._label = QLabel(route.display_name, self)
        self._label.setAlignment(Qt.AlignCenter | Qt.AlignBaseline)
        self._label.setFont(FONT_ROUTE)
        self._label.setDisabled(True)
        self.stackUnder(self._label)

    def resizeEvent(self, p):
        super().resizeEvent(p)
        size = self.geometry().size()
        # XXX: magic number
        size.setHeight(size.height() - 4)
        self._label.resize(size)


class RouteList(QWidget):
    new_route_signal = Signal(Route)

    def _create_route_widget(self, route):
        button = RouteButton(route)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setFont(FONT_ROUTE)

        def cb():
            self.new_route_signal.emit(route)

        button.clicked.connect(cb)
        return button

    def __init__(self, routes):
        super().__init__()

        self.buttons = []
        self.route_per_button = {}

        layout = QVBoxLayout()
        for route in routes:
            button = self._create_route_widget(route)
            self.buttons.append(button)
            self.route_per_button[route] = button
            layout.addWidget(button)

        layout.addStretch(1)

        self.setLayout(layout)


class SearchRouteList(QWidget):
    def __init__(self, routes):
        super().__init__()

        self.route_list = RouteList(routes)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.route_list)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText('Search')
        self.search_line.textChanged.connect(self.search)
        self.search_line.returnPressed.connect(self.select_first_visible)

        layout = QVBoxLayout()
        layout.addWidget(self.search_line)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def search(self):
        text_elements = self.search_line.text().lower().split(' ')

        for button in self.route_list.buttons:
            visible = all(text_element in button.text().lower() for text_element in text_elements)
            button.setVisible(visible)

    def select_first_visible(self):
        for button in self.route_list.buttons:
            if button.isVisible():
                button.animateClick()
                return

    def select_route_with_name(self, name):
        for route, button in self.route_list.route_per_button.items():
            if route.name == name:
                button.animateClick()
                return

    def set_search(self, text):
        self.search_line.setText(text)

    def current_search(self):
        return self.search_line.text()

    def focus(self):
        self.search_line.setFocus()
        self.search_line.selectAll()


TEMPLATE = '''{method} {url}
{headers}

{body}
'''


class TextParameterWidget(QLineEdit):
    updated_signal = Signal(object)

    def __init__(self, parameter):
        super().__init__()
        self.setFont(TEXT_FONT)
        self.setPlaceholderText(parameter.default)
        self.textChanged.connect(self.on_update)

    def on_update(self):
        self.updated_signal.emit(self.text().strip())

    def set_value(self, value):
        if value is None:
            self.setText('')
        else:
            self.setText(value)


class TextFieldParameterWidget(QTextEdit):
    updated_signal = Signal(object)

    def __init__(self, parameter):
        super().__init__()
        metrics = QFontMetrics(TEXT_FONT)
        self.min_height = metrics.height()
        self.setFont(TEXT_FONT)

        self.default_text = parameter.default
        self.textChanged.connect(self.on_update)

        self.highlighter = JSONHighlighter(self.document())
        self.setText(parameter.default)

    def update_size(self):
        size = self.document().size().toSize()
        self.setFixedHeight(max(self.min_height, size.height()) + 3)

    def on_update(self):
        self.update_size()
        self.updated_signal.emit(self.toPlainText().strip())

    def set_value(self, value):
        if value is None:
            self.setText(self.default_text)
        else:
            self.setText(value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_size()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            tc = self.textCursor()
            tc.insertText("  ")
            return
        return QTextEdit.keyPressEvent(self, event)


class ChoiceParameterWidget(QComboBox):
    updated_signal = Signal(object)

    def __init__(self, parameter):
        super().__init__()
        self.activated.connect(self.on_update)
        self.parameter = parameter
        self.addItems(list(map(str, parameter.type.options)))

    def on_update(self, index):
        self.updated_signal.emit(self.parameter.type.options[index])

    def set_value(self, value):
        if value is None:
            value = self.parameter.type.options[0]
        try:
            index = self.parameter.type.options.index(value)
            self.setCurrentIndex(index)
            self.on_update(index)
        except ValueError:
            print('"%s" is not supported for parameter %s' % (value, self.parameter))
            self.setCurrentIndex(0)
            self.on_update(0)


class ParameterWidget(QWidget):
    def __init__(self, route=None):
        super().__init__()

        layout = QVBoxLayout()
        self.route = route

        self.preview_text_edit = QTextEdit()
        self.preview_text_edit.setFont(TEXT_FONT)
        self.preview_text_edit.setReadOnly(True)

        if route is not None:
            if route.group is not None:
                for parameter in route.group.parameters:
                    param_layout = self._create_parameter_layout(
                        route.group.storage_prefix,
                        parameter
                    )
                    layout.addLayout(param_layout)

                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addWidget(line)

            for parameter in route.parameters:
                param_layout = self._create_parameter_layout(
                    route.storage_prefix,
                    parameter
                )
                layout.addLayout(param_layout)

        self.highlighter = TextHighlighter(self.preview_text_edit.document())
        self._update_preview()
        layout.addWidget(self.preview_text_edit)

        self.setLayout(layout)

    def _update_preview(self):
        if self.route is None:
            return

        try:
            group_values, route_values = get_parameter_values_for_route(self.route)
            request = self.route.get_request(group_values, route_values)

            headers = []
            if request.headers is not None:
                headers = ['%s: %s' % (name, value) for name, value in request.headers.items()]

            body = ''
            if request.json is not None:
                body = json.dumps(request.json, indent=2)
            # elif request.body is not None:
            #     body = request.body

            req = PreparedRequest()
            req.prepare_url(request.url, request.params)
            url = req.url

            text = TEMPLATE.format(
                method=request.method,
                url=url,
                headers='\n'.join(headers),
                body=body,
            )

            self.preview_text_edit.setPlainText(text)
        except CaribouException as e:
            self.preview_text_edit.setPlainText(str(e))
        except Exception:
            self.preview_text_edit.setPlainText(traceback.format_exc())

    def _create_parameter_layout(self, prefix, parameter):
        def on_updated_param(value):
            save_parameter(prefix, parameter, value)
            self._update_preview()

        layout = QHBoxLayout()
        label = QLabel(parameter.name)
        label.setFont(FONT)
        layout.addWidget(label)

        if parameter.type is None or isinstance(parameter.type, List):
            widget = TextParameterWidget(parameter)
        elif isinstance(parameter.type, TextField):
            widget = TextFieldParameterWidget(parameter)
        elif isinstance(parameter.type, Choice):
            widget = ChoiceParameterWidget(parameter)
        else:
            raise Exception('Widget not supported')

        widget.updated_signal.connect(on_updated_param)

        saved_value = load_parameter(prefix, parameter)
        widget.set_value(saved_value)

        layout.addWidget(widget)

        if parameter.generator is not None:
            def generate_new_value():
                new_value = parameter.generator()
                widget.set_value(new_value)

            generator_button = QPushButton('new')
            generator_button.clicked.connect(generate_new_value)
            layout.addWidget(generator_button)
        return layout


class WorkerSignals(QObject):
    result = Signal(str, int, float)


class RequestWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            start = time.time()
            r = requests.request(
                *self.args,
                **self.kwargs
            )
            end = time.time()
            elapsed = end - start

            try:
                json_response = r.json()
                text = json.dumps(json_response, indent=2)
            except ValueError:
                text = r.text
            self.signals.result.emit(text, r.status_code, elapsed)
        except Exception:
            self.signals.result.emit(traceback.format_exc(), 0, -1)


class TextHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#E6DB74'))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#AE81FF'))

        get_format = QTextCharFormat()
        get_format.setForeground(QColor('#25A86B'))

        post_format = QTextCharFormat()
        post_format.setForeground(QColor('#FDA60A'))

        if text.startswith('GET '):
            self.setFormat(0, len('GET'), get_format)
        if text.startswith('POST '):
            self.setFormat(0, len('POST'), post_format)

        if len(text) == 0 or text[0] not in '{}[] ':
            return

        current = 0
        for tokentype, value in JsonLexer().get_tokens(text):
            if tokentype in Name or tokentype in String:
                self.setFormat(current, len(value), string_format)
            elif tokentype in Number or tokentype in Keyword:
                self.setFormat(current, len(value), number_format)
            current += len(value)


class JSONHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#E6DB74'))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#AE81FF'))
        if len(text) == 0:
            return

        current = 0
        for tokentype, value in JsonLexer().get_tokens(text):
            if tokentype in Name or tokentype in String:
                self.setFormat(current, len(value), string_format)
            elif tokentype in Number or tokentype in Keyword:
                self.setFormat(current, len(value), number_format)
            current += len(value)


class ResultTextEdit(QPlainTextEdit):
    search = Signal()

    def __init__(self):
        super().__init__()

    def focusInEvent(self, e):
        p = self.palette()
        p.setColor(QPalette.Highlight, QColor("#363636"))
        self.setPalette(p)

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.Find):
            self.search.emit()
            e.accept()
            return
        super().keyPressEvent(e)


class ResultWidget(QWidget):
    def __init__(self, route=None):
        super().__init__()

        layout = QVBoxLayout()
        self.route = route

        self.thread_pool = QThreadPool()

        layout_send = QHBoxLayout()
        self.send_button = QPushButton('Send')
        self.send_button.clicked.connect(self.make_request)

        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText('Search')
        self.search_line.textChanged.connect(self.search_result_reset)
        self.search_line.returnPressed.connect(self.search_result)

        self.response_status_label = QLabel()
        self.response_status_label.setFont(FONT_ROUTE)
        self.response_status_label.hide()

        self.elapsed_time_label = QLabel()
        self.elapsed_time_label.setFont(FONT_ROUTE)
        self.elapsed_time_label.hide()

        self.search_summary_label = QLabel()
        self.search_summary_label.setFont(FONT_ROUTE)
        self.search_summary_label.hide()

        if route is not None:
            layout_send.addWidget(self.send_button)

        layout_send.addWidget(self.response_status_label)
        layout_send.addWidget(self.elapsed_time_label)
        layout_send.addStretch(1)

        layout_send.addWidget(self.search_summary_label)
        layout_send.addWidget(self.search_line)

        layout.addLayout(layout_send)

        self.result_text_edit = ResultTextEdit()
        self.result_text_edit.setReadOnly(True)
        self.result_text_edit.setFont(TEXT_FONT)
        self.result_text_edit.setContextMenuPolicy(Qt.NoContextMenu)

        self.result_text_edit.search.connect(self.focus)

        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self, self.make_request)

        self.result_text_edit.setUndoRedoEnabled(False)

        self.highlighter = TextHighlighter(self.result_text_edit.document())

        layout.addWidget(self.result_text_edit)

        if route is not None:
            saved_result = load_request_result(route)
            self.result_text_edit.setPlainText(saved_result)

        self.setLayout(layout)

    def goto(self, to):
        c = self.result_text_edit.textCursor()
        c.movePosition(to, QTextCursor.MoveAnchor, 1)
        self.result_text_edit.setTextCursor(c)

    def search_result_reset(self):
        self.goto(QTextCursor.Start)

        string_format = QTextCharFormat()
        string_format.setBackground(QColor('#668B8B'))

        extras = []
        self.search_positions = []
        while True:
            extra = QTextEdit.ExtraSelection()
            found = self.result_text_edit.find(self.search_line.text())

            if not found:
                break

            extra.cursor = self.result_text_edit.textCursor()
            extra.format = string_format

            self.search_positions.append(extra.cursor.position())
            extras.append(extra)

        self.result_text_edit.setExtraSelections(extras)
        self.goto(QTextCursor.Start)
        self.search_result()

    def search_result(self):
        p = self.result_text_edit.palette()
        p.setColor(QPalette.Highlight, QColor("#ee799f"))
        self.result_text_edit.setPalette(p)

        search_settings = QTextDocument.FindFlags()

        mod = QApplication.keyboardModifiers()
        if (mod & Qt.ShiftModifier) != 0:
            search_settings |= QTextDocument.FindBackward

        r = self.result_text_edit.find(self.search_line.text(), search_settings)
        if not r:
            if (mod & Qt.ShiftModifier) != 0:
                self.goto(QTextCursor.End)
            else:
                self.goto(QTextCursor.Start)
            self.result_text_edit.find(self.search_line.text(), search_settings)

        if self.search_line.text() == '':
            self.search_summary_label.hide()
            return

        current_position = self.result_text_edit.textCursor().position()
        try:
            current_index = self.search_positions.index(current_position)
        except ValueError:
            current_index = -1

        self.search_summary_label.show()
        self.search_summary_label.setText('%s/%s' % (current_index + 1, len(self.search_positions)))

    def focus(self):
        self.search_line.setFocus()
        self.search_line.selectAll()

    def make_request(self):
        self.response_status_label.hide()
        self.elapsed_time_label.hide()
        self.result_text_edit.setPlainText('Loading..')
        try:
            group_values, route_values = get_parameter_values_for_route(self.route)
            request = self.route.get_request(group_values, route_values)
            worker = RequestWorker(
                request.method,
                request.url,
                params=request.params,
                headers=request.headers,
                json=request.json,
            )
            worker.signals.result.connect(self.set_result)
            self.thread_pool.start(worker)
        except CaribouException as e:
            self.result_text_edit.setPlainText(str(e))
        except Exception:
            self.result_text_edit.setPlainText(traceback.format_exc())

    def set_result(self, text, status_code, elapsed_time):
        if status_code == 0:
            self.response_status_label.hide()
            self.elapsed_time_label.hide()
        else:
            p = self.response_status_label.palette()
            if status_code == 200:
                self.response_status_label.setText(str(status_code) + ' OK')
                p.setColor(QPalette.WindowText, QColor('#1FDA9A'))
            else:
                self.response_status_label.setText(str(status_code) + ' ERROR')
                p.setColor(QPalette.WindowText, QColor('#DB3340'))

            self.response_status_label.setPalette(p)
            self.response_status_label.show()

            self.elapsed_time_label.setText('%s ms' % int(elapsed_time * 1000))
            self.elapsed_time_label.show()

        self.result_text_edit.setUpdatesEnabled(False)
        self.result_text_edit.setPlainText(text)
        self.result_text_edit.setUpdatesEnabled(True)

        save_request_result(self.route, text)
        persist_storage()


class MainWidget(QWidget):
    def __init__(self, routes):
        super().__init__()

        self.layout = QHBoxLayout()

        self.route_list_widget = SearchRouteList(routes)
        self.parameter_widget = ParameterWidget()
        self.result_widget = ResultWidget()

        self.selected_route = None

        self.route_list_widget.route_list.new_route_signal.connect(self.set_route)

        self.layout.addWidget(self.route_list_widget)
        self.layout.addWidget(self.parameter_widget, stretch=1)
        self.layout.addWidget(self.result_widget, stretch=1)

        self.setLayout(self.layout)

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.Find):
            self.route_list_widget.focus()
            e.accept()

    def set_route(self, route):
        self.selected_route = route

        self.layout.removeWidget(self.parameter_widget)
        self.parameter_widget.setParent(None)

        self.layout.removeWidget(self.result_widget)
        self.result_widget.setParent(None)

        self.parameter_widget = ParameterWidget(route)
        self.result_widget = ResultWidget(route)
        self.layout.addWidget(self.parameter_widget, stretch=1)
        self.layout.addWidget(self.result_widget, stretch=1)

    def set_route_with_name(self, name):
        self.route_list_widget.select_route_with_name(name)

    def set_search(self, text):
        self.route_list_widget.set_search(text)

    def current_search(self):
        return self.route_list_widget.current_search()


class MainWindow(QMainWindow):
    def __init__(self, path):
        super().__init__()

        self.widget = None

        if path is None:
            path = load_setting('file_path')

        if path is None:
            path = self.query_new_path()

        if path is None:
            print('No file selected, exiting')
            sys.exit(1)

        self.open_file(path)

        self.statusBar()

        open_action = QAction('&Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('Open config file')
        open_action.triggered.connect(self.query_open)

        reload_action = QAction('&Reload', self)
        reload_action.setShortcut('Ctrl+R')
        reload_action.setStatusTip('Reload config file')
        reload_action.triggered.connect(self.query_reload)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(open_action)
        fileMenu.addAction(reload_action)

        # copy_curl_action = QAction('Copy curl command', self)
        # copy_curl_action.setStatusTip('Copy curl command')
        # copy_curl_action.triggered.connect(self.copy_curl_command)

        # routeMenu = menubar.addMenu('&Route')
        # routeMenu.addAction(copy_curl_action)

        self.setFont(FONT)
        self.setWindowTitle('Caribou')
        self.setWindowIcon(QIcon(os.path.join(CURRENT_DIR, 'icon.png')))

    def query_new_path(self):
        return QFileDialog.getOpenFileName(
            self,
            "Open File", os.path.expanduser("~"), "Python file (*.py)"
        )[0]

    def query_open(self):
        path = self.query_new_path()

        if path is not None:
            self.open_file(path)

    def open_file(self, path):
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.addPath(path)
        self.file_watcher.fileChanged.connect(self.reload)

        save_setting('file_path', path)
        persist_storage()

        self.path = path
        self.reload(path)

    # def copy_curl_command(self):
    #     pass

    def query_reload(self):
        return self.reload(self.path)

    def reload(self, path):
        current_route = self.widget.selected_route if self.widget is not None else None
        current_search = self.widget.current_search() if self.widget is not None else None

        assert path == self.path
        try:
            routes = load_file(self.path)
        except Exception as e:
            msgBox = QMessageBox()
            if isinstance(e, CaribouException):
                msgBox.setText(str(e))
            else:
                msgBox.setText(traceback.format_exc())
            msgBox.exec_()

            routes = []

        if self.widget:
            self.widget.setParent(None)
        self.widget = MainWidget(routes)
        self.setCentralWidget(self.widget)

        if current_route is not None:
            self.widget.set_route_with_name(current_route.name)
        if current_search is not None:
            self.widget.set_search(current_search)


def run(path=None):
    load_storage()

    app = QApplication(sys.argv)
    form = MainWindow(path)

    geometry = app.desktop().availableGeometry()
    width = geometry.width() * 0.8
    height = geometry.height() * 0.8
    form.resize(width, height)

    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
