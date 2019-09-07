import sys
import requests
import json
import traceback
from pygments.token import Name, String, Number, Keyword
from pygments import highlight
from pygments.lexers import guess_lexer, JsonLexer
from pygments.formatters import HtmlFormatter
from PySide2.QtWidgets import (QLabel, QLineEdit, QPushButton, QApplication,
                               QVBoxLayout, QHBoxLayout, QMainWindow, QWidget,
                               QTextEdit, QFrame, QComboBox, QTextBrowser)
from PySide2.QtCore import Signal, QThread, QThreadPool, QRunnable, Slot, QObject, Qt
from PySide2.QtGui import QIcon, QFont, QTextCharFormat, QSyntaxHighlighter, QColor
from .models import Route, Choice
from .loader import load_file
from .storage import save_parameter, load_parameter, get_parameter_values_for_route, load_request_result, save_request_result


class RouteList(QWidget):
    new_route_signal = Signal(Route)

    def _create_route_widget(self, route):
        button = QPushButton(route.display_name)
        button.setCheckable(True)
        button.setAutoExclusive(True)

        def cb():
            self.new_route_signal.emit(route)

        button.clicked.connect(cb)
        return button

    def __init__(self, routes):
        super().__init__()

        layout = QVBoxLayout()
        for route in routes:
            button = self._create_route_widget(route)
            layout.addWidget(button)

        layout.addStretch(1)

        self.setLayout(layout)


TEMPLATE = '''{method} {url}
{headers}

{body}
'''


class TextParameterWidget(QLineEdit):
    updated_signal = Signal(str)

    def __init__(self, parameter, current_value):
        super().__init__()
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
    updated_signal = Signal(str)

    def __init__(self, parameter, current_value):
        super().__init__()
        self.addItems(parameter.cls.options)
        self.default_value = None
        if current_value is not None:
            self.setCurrentText(current_value)
        else:
            self.default_value = parameter.cls.options[0]
            self.setCurrentText(self.default_value)
        self.currentTextChanged.connect(self.on_update)

    def on_update(self, value):
        self.updated_signal.emit(value)

    def set_value(self, value):
        self.setCurrentText(value)


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
        self.preview_text_edit.setFont(QFont('Fira Mono'))
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
                body = json.dumps(request.json, indent=4)
            # elif request.body is not None:
            #     body = request.body

            text = TEMPLATE.format(
                method=request.method,
                url=request.url,
                headers='\n'.join(headers),
                body=body,
            )
            self.preview_text_edit.setPlainText(text)
        except Exception:
            self.preview_text_edit.setPlainText(traceback.format_exc())

    def _create_parameter_layout(self, prefix, parameter):
        def on_updated_param(value):
            global GLOBAL_STORAGE

            save_parameter(prefix, parameter, value)
            self._update_preview()

        layout = QHBoxLayout()
        layout.addWidget(QLabel(parameter.name))

        saved_value = load_parameter(prefix, parameter)

        if parameter.cls is None:
            widget = TextParameterWidget(parameter, saved_value)
        elif isinstance(parameter.cls, Choice):
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

            self.signals.result.emit(r.text)
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
        layout_send.addWidget(self.send_button)

        layout.addLayout(layout_send)

        self.result_text_edit = QTextEdit()
        self.result_text_edit.setReadOnly(True)
        self.result_text_edit.setFont(QFont('Fira Mono'))

        self.highlighter = TextHighlighter(self.result_text_edit.document())

        layout.addWidget(self.result_text_edit)

        if route is not None:
            saved_result = load_request_result(route)
            self.result_text_edit.setPlainText(saved_result)

        self.setLayout(layout)

    def make_request(self):
        self.result_text_edit.setPlainText('Loading..')
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

    def set_result(self, text):
        self.result_text_edit.setPlainText(text)
        save_request_result(self.route, text)


class MainWidget(QWidget):
    def __init__(self, routes):
        super().__init__()

        self.layout = QHBoxLayout()

        self.route_list_widget = RouteList(routes)
        self.parameter_widget = ParameterWidget()
        self.result_widget = ResultWidget()

        self.route_list_widget.new_route_signal.connect(self.set_route)

        self.layout.addWidget(self.route_list_widget)
        self.layout.addWidget(self.parameter_widget)
        self.layout.addWidget(self.result_widget)

        self.setLayout(self.layout)

    def set_route(self, route):
        self.layout.removeWidget(self.parameter_widget)
        self.parameter_widget.setParent(None)

        self.layout.removeWidget(self.result_widget)
        self.result_widget.setParent(None)

        self.parameter_widget = ParameterWidget(route)
        self.result_widget = ResultWidget(route)
        self.layout.addWidget(self.parameter_widget)
        self.layout.addWidget(self.result_widget)


class MainWindow(QMainWindow):
    def __init__(self, routes):
        super().__init__()

        self.widget = MainWidget(routes)
        self.setCentralWidget(self.widget)
        self.setWindowTitle('Caribou')
        self.setWindowIcon(QIcon('icon.png'))
        self.resize(1100, 600)


def run(path):
    routes = load_file(path)

    app = QApplication(sys.argv)
    form = MainWindow(routes)
    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
