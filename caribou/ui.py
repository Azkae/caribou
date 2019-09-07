import sys
import json
import traceback
from PySide2.QtWidgets import (QLabel, QLineEdit, QPushButton, QApplication,
                               QVBoxLayout, QHBoxLayout, QMainWindow, QWidget, QTextEdit, QFrame)
from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon, QFont
from .models import Route
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


class ParameterWidget(QWidget):
    def __init__(self, route=None):
        super().__init__()

        layout = QVBoxLayout()
        self.route = route

        if route is not None:
            if route.group is not None:
                for parameter in route.group.parameters:
                    param_layout, line_edit = self._create_parameter_layout(
                        route.group.storage_prefix,
                        parameter
                    )
                    layout.addLayout(param_layout)

                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addWidget(line)

            for parameter in route.parameters:
                param_layout, line_edit = self._create_parameter_layout(
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
        layout = QHBoxLayout()

        layout.addWidget(QLabel(parameter.name))

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(parameter.default)

        saved_value = load_parameter(prefix, parameter)
        if saved_value is not None:
            line_edit.setText(saved_value)

        def update_storage():
            global GLOBAL_STORAGE

            save_parameter(prefix, parameter, line_edit.text())
            self._update_preview()

        line_edit.textChanged.connect(update_storage)

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        routes = load_file('ex.py')
        # routes = [
        #     Route('GET', 'users', [], {}),
        #     Route('POST', 'user', [Parameter(name='user_id', default_value='default value')], {'Authorization': 'Basic test'}, '{"user_id": "{{ user_id }}"}'),
        #     Route('GET', 'movie by id', [Parameter(name='test2')], {}),
        #     Route('GET', 'movies', [Parameter(name='test3')], {}),
        #     Route('POST', 'movie', [Parameter(name='test4')], {}),
        # ]

        self.widget = MainWidget(routes)
        self.setCentralWidget(self.widget)
        self.setWindowTitle('Caribou')
        self.setWindowIcon(QIcon('icon.png'))
        self.resize(900, 600)


def run():
    # Create the Qt Application
    app = QApplication(sys.argv)
    # QApplication.setFont(QFont('Roboto'))
    # Create and show the form
    form = MainWindow()
    form.show()
    # Run the main Qt loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
