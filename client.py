import sys
import os
import socket
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QFileDialog
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPainter
import logging
from tqdm import tqdm


logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class FileTransferThread(QThread):
    progress_signal = pyqtSignal(int)

    def __init__(self, host, port, file_path):
        super().__init__()
        self.host = host
        self.port = port
        self.file_path = file_path

    def run(self):
        buffer_size = 8192
        file_name = os.path.basename(self.file_path)
        file_size = os.path.getsize(self.file_path)

        logging.info(f"Connecting to {self.host}:{self.port}...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.host, self.port))
        logging.info("Connected!")

        logging.info(f"Sending file: {file_name} ({file_size} bytes)")
        file_name_length = len(file_name.encode())
        client_socket.sendall(file_name_length.to_bytes(4, 'big'))
        client_socket.sendall(file_name.encode())
        client_socket.sendall(file_size.to_bytes(8, 'big'))

        with open(self.file_path, 'rb') as f:
            sent = 0
            progress_bar = tqdm(total=file_size, unit='B', unit_scale=True)
            while sent < file_size:
                data = f.read(buffer_size)
                if not data:
                    break
                client_socket.sendall(data)
                sent += len(data)
                self.progress_signal.emit(sent)
                progress_bar.update(len(data))
            progress_bar.close()

        client_socket.close()
        logging.info("File transfer completed.")


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('File Transfer Client')
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(40, 40, 40))
        palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Highlight, QColor(170, 0, 0))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        self.setPalette(palette)

        button_style = """
        QPushButton {
            background-color: rgb(30, 30, 30);
            color: rgb(255, 255, 255);
            border: 1px solid rgb(170, 0, 0);
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: rgb(40, 40, 40);
            border: 1px solid rgb(200, 0, 0);
        }
        QPushButton:pressed {
            background-color: rgb(50, 50, 50);
            border: 1px solid rgb(255, 0, 0);
        }
        """
        self.setStyleSheet(button_style)

        layout = QVBoxLayout()

        # Add a container for the IP and file labels and entries
        container = QWidget()
        container.setAutoFillBackground(True)
        container_palette = container.palette()
        container_palette.setColor(QPalette.Window, QColor(50, 50, 50))
        container.setPalette(container_palette)

        container_layout = QVBoxLayout()

        ip_label = QLabel('Server IP Address:')
        container_layout.addWidget(ip_label)

        self.ip_entry = QLineEdit()
        container_layout.addWidget(self.ip_entry)

        file_label = QLabel('File Path:')
        container_layout.addWidget(file_label)

        self.file_entry = QLineEdit()
        container_layout.addWidget(self.file_entry)

        container.setLayout(container_layout)

        layout.addWidget(container)

        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(self.browse_files)
        layout.addWidget(browse_button)

        self.transfer_button = QPushButton('Start Transfer')
        self.transfer_button.clicked.connect(self.start_transfer)
        layout.addWidget(self.transfer_button)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.setLayout(layout)

        # Add this code at the end of the init_ui method
        self.animation_offset = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_background_animation)
        self.animation_timer.start(50)


    def browse_files(self):
        file_path, _ = QFileDialog.getOpenFileName()
        self.file_entry.setText(file_path)

    def start_transfer(self):
        host = self.ip_entry.text()
        port = 12345
        file_path = self.file_entry.text()

        self.transfer_button.setEnabled(False)
        try:
            self.progress.setMaximum(os.path.getsize(file_path))    
        except:
            pass

        self.transfer_thread = FileTransferThread(host, port, file_path)
        self.transfer_thread.progress_signal.connect(self.update_progress)
        self.transfer_thread.finished.connect(self.transfer_finished)
        self.transfer_thread.start()

    def update_progress(self, sent):
        self.progress.setValue(sent)

    def transfer_finished(self):
        self.transfer_button.setEnabled(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        for i in range(0, self.width(), 10):
            painter.setPen(QColor(170, 0, 0, 255 - i % 255))
            painter.drawLine(i + self.animation_offset, 0, i + self.animation_offset, self.height())
        painter.end()


    def update_background_animation(self):
        self.animation_offset += 1
        if self.animation_offset >= 10:
            self.animation_offset = 0
        self.update()


def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

