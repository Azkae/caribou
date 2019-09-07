import sys
import json
import traceback
from PySide2.QtWidgets import (QLabel, QLineEdit, QPushButton, QApplication,
                               QVBoxLayout, QHBoxLayout, QMainWindow, QWidget,
                               QTextEdit, QFrame, QComboBox)
from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon, QFont
from .models import Route, Choice
from .loader import load_file
from .storage import save_parameter, load_parameter, get_parameter_values


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
        self._update_preview()

        layout.addWidget(self.preview_text_edit)

        self.setLayout(layout)

    def _update_preview(self):
        if self.route is None:
            return

        try:
            if self.route.group is not None:
                group_values = get_parameter_values(
                    self.route.group.storage_prefix,
                    self.route.group.parameters
                )
            else:
                group_values = {}

            route_values = get_parameter_values(
                self.route.storage_prefix,
                self.route.parameters
            )

            request = self.route.get_request(group_values, route_values)

            headers = ['%s: %s' % (name, value) for name, value in request.headers.items()]
            body = ''
            if request.json is not None:
                body = json.dumps(request.json, indent=4)
            elif request.body is not None:
                body = request.body

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


class MainWidget(QWidget):
    def __init__(self, routes):
        super().__init__()

        self.layout = QHBoxLayout()

        self.route_list_widget = RouteList(routes)
        self.parameter_widget = ParameterWidget()

        self.route_list_widget.new_route_signal.connect(self.set_route)

        self.layout.addWidget(self.route_list_widget)
        self.layout.addWidget(self.parameter_widget)

        self.setLayout(self.layout)

    def set_route(self, route):
        self.layout.removeWidget(self.parameter_widget)
        self.parameter_widget.setParent(None)
        self.parameter_widget = ParameterWidget(route)
        self.layout.addWidget(self.parameter_widget)


class MainWindow(QMainWindow):
    def __init__(self, routes):
        super().__init__()

        self.widget = MainWidget(routes)
        self.setCentralWidget(self.widget)
        self.setWindowTitle('Caribou')
        self.setWindowIcon(QIcon('icon.png'))
        self.resize(900, 600)


def run(path):
    routes = load_file(path)

    app = QApplication(sys.argv)
    form = MainWindow(routes)
    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
