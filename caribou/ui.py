import sys
import os
import requests
import json
import traceback
from pygments.token import Name, String, Number, Keyword
from pygments.lexers import JsonLexer
from PySide2.QtWidgets import (QLabel, QLineEdit, QPushButton, QApplication,
                               QVBoxLayout, QHBoxLayout, QMainWindow, QWidget,
                               QTextEdit, QPlainTextEdit, QFrame, QComboBox, QScrollArea, QShortcut)
from PySide2.QtCore import Signal, QThreadPool, QRunnable, Slot, QObject, Qt
from PySide2.QtGui import QIcon, QFont, QTextCharFormat, QSyntaxHighlighter, QColor, QKeySequence, QTextDocument, QTextCursor
from .models import Route, Choice
from .loader import load_file
from .storage import save_parameter, load_parameter, get_parameter_values_for_route, load_request_result, save_request_result, MissingParameter, persist_storage, load_storage

CURRENT_DIR = os.path.dirname(__file__)

FONT = QFont('Fira Mono')
TEXT_FONT = QFont('Fira Mono')


class RouteList(QWidget):
    new_route_signal = Signal(Route)

    def _create_route_widget(self, route):
        button = QPushButton(route.display_name)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setFont(FONT)

        def cb():
            self.new_route_signal.emit(route)

        button.clicked.connect(cb)
        return button

    def __init__(self, routes):
        super().__init__()

        self.buttons = []

        layout = QVBoxLayout()
        for route in routes:
            button = self._create_route_widget(route)
            self.buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)

        self.setLayout(layout)


class SearchRouteList(QWidget):
    def __init__(self, routes):
        super().__init__()

        self.route_list = RouteList(routes)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.route_list)
        self.scroll_area.setWidgetResizable(True)

        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText('Search')
        self.search_line.textChanged.connect(self.search)
        self.search_line.returnPressed.connect(self.select_first_visible)

        layout = QVBoxLayout()
        layout.addWidget(self.search_line)
        layout.addWidget(self.scroll_area)

        self.shortcut = QShortcut(QKeySequence("Ctrl+f"), self, self.focus)

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

    def focus(self):
        self.search_line.setFocus()
        self.search_line.selectAll()


TEMPLATE = '''{method} {url}
{headers}

{body}
'''


class TextParameterWidget(QLineEdit):
    updated_signal = Signal(object)

    def __init__(self, parameter, current_value):
        super().__init__()
        self.setFont(TEXT_FONT)
        self.setPlaceholderText(parameter.default)
        self.default_value = None
        if current_value is not None:
            self.setText(current_value)
        self.textChanged.connect(self.on_update)

    def on_update(self):
        self.updated_signal.emit(self.text())

    def set_value(self, value):
        self.setText(value)


class ChoiceParameterWidget(QComboBox):
    updated_signal = Signal(object)

    def __init__(self, parameter, current_value):
        super().__init__()
        self.currentIndexChanged.connect(self.on_update)
        self.parameter = parameter
        self.addItems(list(map(str, parameter.type.options)))
        self.default_value = None
        if current_value is not None:
            try:
                self.set_value(current_value)
            except Exception as e:
                self.setCurrentIndex(0)
                print(e)
        else:
            self.default_value = parameter.type.options[0]
            self.setCurrentIndex(0)

    def on_update(self, index):
        self.updated_signal.emit(self.parameter.type.options[index])

    def set_value(self, value):
        try:
            index = self.parameter.type.options.index(value)
            self.setCurrentIndex(index)
        except ValueError:
            print('Value %s not supported for parameter %s' % self.parameter)


class ParameterWidget(QWidget):
    def __init__(self, route=None):
        super().__init__()

        layout = QVBoxLayout()
        self.route = route

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

        self.preview_text_edit = QTextEdit()
        self.preview_text_edit.setFont(TEXT_FONT)
        self.preview_text_edit.setReadOnly(True)

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

            text = TEMPLATE.format(
                method=request.method,
                url=request.url,
                headers='\n'.join(headers),
                body=body,
            )
            self.preview_text_edit.setPlainText(text)
        except MissingParameter as e:
            self.preview_text_edit.setPlainText('Missing parameter: %s' % e.parameter_name)
        except Exception:
            self.preview_text_edit.setPlainText(traceback.format_exc())

    def _create_parameter_layout(self, prefix, parameter):
        def on_updated_param(value):
            global GLOBAL_STORAGE

            save_parameter(prefix, parameter, value)
            self._update_preview()

        layout = QHBoxLayout()
        label = QLabel(parameter.name)
        label.setFont(FONT)
        layout.addWidget(label)

        saved_value = load_parameter(prefix, parameter)

        if parameter.type is None:
            widget = TextParameterWidget(parameter, saved_value)
        elif isinstance(parameter.type, Choice):
            widget = ChoiceParameterWidget(parameter, saved_value)
        else:
            raise Exception('Widget not supported')

        if widget.default_value is not None:
            save_parameter(prefix, parameter, widget.default_value)

        widget.updated_signal.connect(on_updated_param)

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
    result = Signal(str)


class RequestWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            r = requests.request(
                *self.args,
                **self.kwargs
            )

            try:
                json_response = r.json()
                text = json.dumps(json_response, indent=2)
            except ValueError:
                text = r.text
            self.signals.result.emit(text)
        except Exception:
            self.signals.result.emit(traceback.format_exc())


class TextHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#E6DB74'))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#AE81FF'))

        if len(text) == 0 or text[0] not in '{}[] ':
            return

        current = 0
        for tokentype, value in JsonLexer().get_tokens(text):
            if tokentype in Name or tokentype in String:
                self.setFormat(current, len(value), string_format)
            elif tokentype in Number or tokentype in Keyword:
                self.setFormat(current, len(value), number_format)
            current += len(value)


class ResultWidget(QWidget):
    def __init__(self, route=None):
        super().__init__()

        layout = QVBoxLayout()
        self.route = route

        self.thread_pool = QThreadPool()

        layout_send = QHBoxLayout()
        self.send_button = QPushButton('Send')
        self.send_button.clicked.connect(self.make_request)

        layout_send.addStretch(1)

        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText('Search')
        self.search_line.textChanged.connect(self.search_result_reset)
        self.search_line.returnPressed.connect(self.search_result)

        layout_send.addWidget(self.search_line)
        layout_send.addWidget(self.send_button)

        layout.addLayout(layout_send)

        self.result_text_edit = QPlainTextEdit()
        self.result_text_edit.setReadOnly(True)
        self.result_text_edit.setFont(TEXT_FONT)
        self.result_text_edit.setContextMenuPolicy(Qt.NoContextMenu)

        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+f"), self, self.focus)
        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self, self.make_request)

        self.result_text_edit.setUndoRedoEnabled(False)

        self.highlighter = TextHighlighter(self.result_text_edit.document())

        layout.addWidget(self.result_text_edit)

        if route is not None:
            saved_result = load_request_result(route)
            self.result_text_edit.setPlainText(saved_result)

        self.setLayout(layout)

    def goto_start(self):
        c = self.result_text_edit.textCursor()
        c.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor, 1)
        self.result_text_edit.setTextCursor(c)

    def search_result_reset(self):
        self.goto_start()
        self.search_result()

    def search_result(self):
        r = self.result_text_edit.find(self.search_line.text(), QTextDocument.FindCaseSensitively)
        if not r:
            self.goto_start()

    def focus(self):
        self.search_line.setFocus()
        self.search_line.selectAll()

    def make_request(self):
        self.result_text_edit.setPlainText('Loading..')
        try:
            group_values, route_values = get_parameter_values_for_route(self.route)
            request = self.route.get_request(group_values, route_values)
            worker = RequestWorker(
                request.method,
                request.url,
                headers=request.headers,
                json=request.json,
            )
            worker.signals.result.connect(self.set_result)
            self.thread_pool.start(worker)
        except MissingParameter as e:
            self.result_text_edit.setPlainText('Missing parameter: %s' % e.parameter_name)
        except Exception:
            self.result_text_edit.setPlainText(traceback.format_exc())

    def set_result(self, text):
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

        self.route_list_widget.route_list.new_route_signal.connect(self.set_route)

        self.layout.addWidget(self.route_list_widget)
        self.layout.addWidget(self.parameter_widget, stretch=1)
        self.layout.addWidget(self.result_widget, stretch=1)

        self.setLayout(self.layout)

    def set_route(self, route):
        self.layout.removeWidget(self.parameter_widget)
        self.parameter_widget.setParent(None)

        self.layout.removeWidget(self.result_widget)
        self.result_widget.setParent(None)

        self.parameter_widget = ParameterWidget(route)
        self.result_widget = ResultWidget(route)
        self.layout.addWidget(self.parameter_widget, stretch=1)
        self.layout.addWidget(self.result_widget, stretch=1)


class MainWindow(QMainWindow):
    def __init__(self, routes):
        super().__init__()

        self.setFont(FONT)
        self.widget = MainWidget(routes)
        self.setCentralWidget(self.widget)
        self.setWindowTitle('Caribou')
        self.setWindowIcon(QIcon(os.path.join(CURRENT_DIR, 'icon.png')))


def run(path):
    load_storage()
    routes = load_file(path)

    app = QApplication(sys.argv)
    form = MainWindow(routes)

    geometry = app.desktop().availableGeometry()
    width = geometry.width() * 0.8
    height = geometry.height() * 0.8
    form.resize(width, height)

    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
