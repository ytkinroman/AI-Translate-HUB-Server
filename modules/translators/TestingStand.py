from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
import sys
from modules.translators.FirstTranslator import Translator


class SimpleInterface(QWidget):
    def __init__(self, translator):
        super().__init__()
        self.init_ui(translator)

    def init_ui(self, translator):
        self.setWindowTitle("Demonstration stand")
        self.setGeometry(100, 100, 300, 200)

        self._translator = translator

        self.layout = QVBoxLayout()

        self.language_selector = QComboBox(self)
        self.language_selector.addItems(["English", "Russian", "French", "German"])
        self.layout.addWidget(self.language_selector)

        self.entry = QLineEdit(self)
        self.layout.addWidget(self.entry)

        self.button = QPushButton("Submit", self)
        self.button.clicked.connect(self.process_input)
        self.layout.addWidget(self.button)

        self.output_label = QLabel("Result: ", self)
        self.layout.addWidget(self.output_label)

        self.setLayout(self.layout)

    def process_input(self):
        data = {
            "text": self.entry.text(),
            "lang": self.language_selector.currentText()
        }
        result = self._translator.execute(data)
        self.output_label.setText(f"Result: {result['text']}\nLanguage: {result['lang']}")


if __name__ == "__main__":
    translator = Translator()
    app = QApplication(sys.argv)
    window = SimpleInterface(translator)
    window.show()
    sys.exit(app.exec_())