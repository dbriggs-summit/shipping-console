
class CancelledOrderException(Exception):
    def __init__(self, order_no):
        self.order_no = order_no
        self.message = f'Order # {self.order_no} has been cancelled. DO NOT SHIP'

    def __str__(self):
        return self.message


class OrderDoesNotExistException(Exception):
    def __init__(self, order_no):
        self.order_no = order_no
        self.message = f'Order # {self.order_no} does not exist, or all lines have already been scanned'

    def __str__(self):
        return self.message