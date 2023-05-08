import sys
import os
import socket
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QFrame
from PyQt5.QtGui import QPalette, QColor, QPainter
from rich.progress import Progress
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem



received_files_dir = "C:/Users/adiaz/OneDrive/Escritorio/Files Received/received_files"

class FileReceiveThread(QThread):
    status_signal = pyqtSignal(str)
    file_received_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, host, port, received_files_dir):
        super().__init__()
        self.host = host
        self.port = port
        self.received_files_dir = received_files_dir

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(1)

        self.status_signal.emit(f"Server listening on {self.host}:{self.port}")

        while True:
            conn, addr = server_socket.accept()
            self.status_signal.emit(f"Connected to {addr}")

            file_name_length = int.from_bytes(conn.recv(4), 'big')
            file_name = conn.recv(file_name_length).decode()
            file_size = int.from_bytes(conn.recv(8), 'big')
            file_path = os.path.join(self.received_files_dir, file_name)

            self.receive_file(conn, file_path, file_size)
            self.file_received_signal.emit(file_name)

            conn.close()

    def receive_file(self, conn, file_path, file_size):
        buffer_size = 8192
        received_size = 0

        with open(file_path, 'wb') as f:
            while received_size < file_size:
                data = conn.recv(buffer_size)
                if not data:
                    break
                f.write(data)
                received_size += len(data)
                progress = int(received_size / file_size * 100)
                self.progress_signal.emit(progress)

        if received_size == file_size:
            self.progress_signal.emit(100)


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('File Transfer Server')
        self.setAutoFillBackground(True)
        received_files_dir = 'received_files'
        if not os.path.exists(received_files_dir):
            os.makedirs(received_files_dir)


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

        progress_bar_style = """
        QProgressBar {
            background-color: rgb(30, 30, 30);
            border: 1px solid rgb(170, 0, 0);
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 rgba(170, 0, 0, 180), stop: 0.5 rgba(255, 0, 0, 255), stop: 1 rgba(170, 0, 0, 180));
        }
        """
        self.setStyleSheet(progress_bar_style)

        layout = QVBoxLayout()

        self.status_label = QLabel('')
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgb(30, 30, 30);
                color: white;
                border: 1px solid rgb(170, 0, 0);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status_frame.setLineWidth(2)
        self.status_frame.setStyleSheet("QFrame {border-color: rgb(170, 0, 0);}")
        self.status_frame_layout = QVBoxLayout(self.status_frame)
        self.status_frame_layout.addWidget(self.status_label)
        layout.addWidget(self.status_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(['Received Files'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.setLayout(layout)
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["File Name", "Type", "Size"])
        self.file_table.setAlternatingRowColors(True)
        self.update_file_table()
        layout.addWidget(self.file_table)


        # Add this code at the end of the init_ui method
        self.animation_offset = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_background_animation)
        self.animation_timer.start(50)

        self.received_files_dir = 'received_files'
        if not os.path.exists(self.received_files_dir):
            os.makedirs(self.received_files_dir)

        self.file_receive_thread = FileReceiveThread('0.0.0.0', 12345, self.received_files_dir)
        self.file_receive_thread.status_signal.connect(self.update_status)
        self.file_receive_thread.file_received_signal.connect(self.add_received_file)
        self.file_receive_thread.progress_signal.connect(self.progress.setValue)
        self.file_receive_thread.start()

    def update_status(self, status):
        self.status_label.setText(status)

    def add_received_file(self, file_name):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        self.table.setItem(row_count, 0, QTableWidgetItem(file_name))

    def paintEvent(self, event):
        painter = QPainter(self)
        for i in range(0, self.height(), 10):
            painter.setPen(QColor(170, 0, 0))
            painter.drawLine(0, i + self.animation_offset, self.width(), i + self.animation_offset)
        painter.end()

    def update_background_animation(self):
        self.animation_offset -= 1
        if self.animation_offset <= -10:
            self.animation_offset = 0
        self.update()
    
    def file_received(self, file_name):
        self.update_file_table()

    def update_file_table(self):
        files = [f for f in os.listdir(received_files_dir) if os.path.isfile(os.path.join(received_files_dir, f))]
        self.file_table.setRowCount(len(files))

        for row, file in enumerate(files):
            file_path = os.path.join(received_files_dir, file)
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / 1024 / 1024
            file_type = os.path.splitext(file)[1]

            if file_size_mb >= 1024:
                file_size_str = f"{file_size_mb / 1024:.2f} GB"
            else:
                file_size_str = f"{file_size_mb:.2f} MB"

            self.file_table.setItem(row, 0, QTableWidgetItem(file))
            self.file_table.setItem(row, 1, QTableWidgetItem(file_type))
            self.file_table.setItem(row, 2, QTableWidgetItem(file_size_str))




def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()