class CaribouException(Exception):
    pass


class MissingParameter(CaribouException):
    def __init__(self, parameter_name):
        self.parameter_name = parameter_name

    def __str__(self):
        return 'Missing parameter: %s' % self.parameter_name
