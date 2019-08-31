import os
import sys
from typing import NamedTuple, List
from PySide2.QtWidgets import (QLabel, QLineEdit, QPushButton, QApplication,
                               QVBoxLayout, QHBoxLayout, QDialog, QMainWindow, QWidget, QTextEdit)
from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon


class Parameter(NamedTuple):
    name: str
    default_value: str = ''


class Route(NamedTuple):
    method: str
    name: str
    parameters: List[Parameter]
    headers: dict
    body: str = ''


class RouteList(QWidget):
    new_route_signal = Signal(Route)

    def _create_route_widget(self, route):
        def cb():
             self.new_route_signal.emit(route)

        button = QPushButton(route.method + ' ' + route.name)

        button.clicked.connect(cb)
        return button

    def __init__(self, routes):
        super().__init__()

        layout = QVBoxLayout()
        for route in routes:
            layout.addWidget(self._create_route_widget(route))

        layout.addStretch(1)

        self.setLayout(layout)


TEMPLATE = '''{method} {url}
{headers}

{body}
'''


class ParameterWidget(QWidget):
    def __init__(self, route=None):
        super().__init__()

        layout = QVBoxLayout()

        self.parameters = {}
        self.route = route

        if route is not None:
            for parameter in route.parameters:
                param_layout, line_edit = self._create_parameter_layout(parameter)

                self.parameters[parameter] = line_edit
                layout.addLayout(param_layout)

        self.preview_text_edit = QTextEdit()
        self.preview_text_edit.setReadOnly(True)
        self._update_preview()

        layout.addWidget(self.preview_text_edit)

        self.setLayout(layout)

    def _update_preview(self):
        if self.route is None:
            return

        headers = ['%s: %s' % (name, value) for name, value in self.route.headers.items()]

        text = TEMPLATE.format(
            method=self.route.method,
            url=self.route.name,
            headers='\n'.join(headers),
            body=self.route.body
        )

        self.preview_text_edit.setPlainText(text)

    def _create_parameter_layout(self, parameter):
        layout = QHBoxLayout()

        layout.addWidget(QLabel(parameter.name))

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(parameter.default_value)
        line_edit.textChanged.connect(self._update_preview)

        layout.addWidget(line_edit)

        return layout, line_edit


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


class Form(QMainWindow):
    def __init__(self):
        super().__init__()

        routes = [
            Route('GET', 'users', [], {}),
            Route('POST', 'user', [Parameter(name='test', default_value='default value')], {'Authorization': 'Basic test'}),
            Route('GET', 'movie by id', [Parameter(name='test2')], {}),
            Route('GET', 'movies', [Parameter(name='test3')], {}),
            Route('POST', 'movie', [Parameter(name='test4')], {}),
        ]

        self.widget = MainWidget(routes)
        self.setCentralWidget(self.widget)
        self.setWindowTitle('Caribou')
        self.setWindowIcon(QIcon('icon.png'))


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication(sys.argv)
    # Create and show the form
    form = Form()
    form.show()
    # Run the main Qt loop
    sys.exit(app.exec_())
