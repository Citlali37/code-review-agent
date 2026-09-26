def divide(a, b):
    return a / b


def calculate(expression):
    return eval(expression)


def parse_number(value):
    try:
        return int(value)
    except:
        return 0
