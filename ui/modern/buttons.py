from PyQt5.QtWidgets import QPushButton


class PrimaryButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primary")


class SecondaryButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("secondary")


class DangerButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("danger")
