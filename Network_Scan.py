import sys
import os
import threading
import time
from collections import deque
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QPushButton, QGroupBox, 
                             QLabel, QListWidget, QListWidgetItem, QSplitter, QFrame)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

PIPE_PATH = "/tmp/lkim_telemetry.fifo"

# --- СТИЛИЗАЦИЯ (КИБЕРПАНК ТЕРМИНАЛ) ---
STYLE = """
QMainWindow { background-color: #0b0e14; }
QGroupBox { 
    color: #00ff41; border: 1px solid #1a1f26; 
    border-radius: 4px; margin-top: 10px; font-weight: bold; font-size: 11px;
}
QListWidget { 
    background-color: #0d1117; border: none; color: #8b949e; 
    font-family: 'Consolas'; font-size: 12px; outline: none;
}
QListWidget::item { padding: 5px; border-bottom: 1px solid #1a1f26; }
QListWidget::item:selected { background-color: #1a1f26; color: #00ff41; }
QTextBrowser { background-color: #010409; border: none; color: #c9d1d9; font-size: 12px; }
#StatusBar { background-color: #161b22; color: #58a6ff; font-weight: bold; border-top: 1px solid #30363d; }
#HeaderLabel { color: #00ff41; font-size: 16px; font-family: 'Courier New'; }
"""

class NetworkScanApp(QMainWindow):
    data_received = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LKIM | NETWORK INTEGRITY DESIGNER")
        self.setGeometry(50, 50, 1500, 900)
        self.setStyleSheet(STYLE)

        # Буфер данных (последние 40 пакетов)
        self.history = deque(maxlen=40)
        
        self.setup_ui()
        self.start_pipe_listener()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_vbox = QVBoxLayout(central_widget)

        # --- ВЕРХНЯЯ ПАНЕЛЬ (Header) ---
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_label = QLabel("LIVE STREAM: [ACTIVE SESSION]")
        header_label.setObjectName("HeaderLabel")
        header_layout.addWidget(header_label)
        main_vbox.addWidget(header)

        # --- ОСНОВНАЯ ЧАСТЬ (Splitter) ---
        splitter_main = QSplitter(Qt.Horizontal)

        # 1. Левая панель: Хосты и Порты
        left_panel = QGroupBox("Network Nodes / Ports")
        left_layout = QVBoxLayout()
        self.nodes_list = QListWidget()
        # Заполним "рыбой" для демонстрации интерфейса
        self.populate_mock_nodes()
        self.nodes_list.itemClicked.connect(self.on_node_clicked)
        left_layout.addWidget(self.nodes_list)
        left_panel.setLayout(left_layout)
        splitter_main.addWidget(left_panel)

        # 2. Центральная панель: 3D График
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.fig = Figure(facecolor='#0b0e14')
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        center_layout.addWidget(self.canvas)
        splitter_main.addWidget(center_widget)

        # 3. Правая панель: Инспектор
        right_panel = QGroupBox("Threat Inspector")
        right_layout = QVBoxLayout()
        self.ins_browser = QTextBrowser()
        right_layout.addWidget(self.ins_browser)
        right_panel.setLayout(right_layout)
        splitter_main.addWidget(right_panel)

        splitter_main.setStretchFactor(1, 4) # График шире всех
        main_vbox.addWidget(splitter_main, stretch=5)

        # --- НИЖНЯЯ ПАНЕЛЬ (Description & Status) ---
        bottom_splitter = QSplitter(Qt.Horizontal)

        # Слева-снизу: Текущая активность
        self.activity_panel = QGroupBox("Action Monitor")
        act_layout = QVBoxLayout()
        self.act_label = QLabel("IDLE: Waiting for data...")
        self.act_label.setStyleSheet("color: #8b949e; font-style: italic;")
        act_layout.addWidget(self.act_label)
        self.activity_panel.setLayout(act_layout)
        bottom_splitter.addWidget(self.activity_panel)

        # Справа-снизу: Детальное описание
        self.desc_panel = QGroupBox("Detailed System Event Log")
        desc_layout = QVBoxLayout()
        self.desc_browser = QTextBrowser()
        desc_layout.addWidget(self.desc_browser)
        self.desc_panel.setLayout(desc_layout)
        bottom_splitter.addWidget(self.desc_panel)

        bottom_splitter.setStretchFactor(1, 3)
        main_vbox.addWidget(bottom_splitter, stretch=2)

    def populate_mock_nodes(self):
        nodes = [
            ("127.0.0.1:80", "ACTIVE", "#3fb950"),
            ("192.168.1.1:443", "SECURE", "#3fb950"),
            ("UNKNOWN:666", "SUSPICIOUS", "#f85149"),
            ("0.0.0.0:22", "LISTENING", "#58a6ff")
        ]
        for name, status, color in nodes:
            item = QListWidgetItem(f"● {name} [{status}]")
            item.setForeground(QColor(color))
            self.nodes_list.addItem(item)

    def on_node_clicked(self, item):
        self.act_label.setText(f"INSPECTING: {item.text()}")
        self.desc_browser.append(f"<span style='color:#58a6ff;'>[INFO]</span> Запрос данных по узлу {item.text()}...")

    def update_3d_candles(self):
        self.ax.clear()
        self.ax.set_facecolor('#0b0e14')
        self.ax.grid(False)

        if not self.history:
            self.canvas.draw()
            return

        # Настройки свечей
        dx = dy = 0.5  # Фиксированная ширина (теперь они не растянуты!)
        
        for i, data in enumerate(self.history):
            _, tx, rx, score, alert = data
            tx, rx, score = float(tx), float(rx), int(score)
            
            # Позиция X (время), Y (направление, пусть 0), Z (высота)
            x_pos = i
            y_pos = 0
            
            color_tx = '#2ea043' if score > 80 else '#da3633'
            color_rx = '#0366d6' if score > 80 else '#da3633'

            # Рисуем "тело" свечи TX (вверх)
            self.ax.bar3d(x_pos, y_pos, 0, dx, dy, tx, color=color_tx, alpha=0.8)
            # Рисуем "тело" свечи RX (вниз зеркально)
            self.ax.bar3d(x_pos, y_pos, 0, dx, dy, -rx, color=color_rx, alpha=0.6)

        self.ax.set_zlim(-100, 100)
        self.ax.axis('off') # Для футуристичного вида
        self.canvas.draw()

    def handle_new_data(self, data):
        self.history.append(data)
        ts, tx, rx, score, alert = data
        
        self.act_label.setText(f"PROCESSING PKT: {ts}")
        self.desc_browser.append(f"[{time.strftime('%H:%M:%S')}] Traffic: IN={rx}KB, OUT={tx}KB | Integrity={score}%")
        
        if alert != "NONE":
            self.ins_browser.setHtml(f"<h3 style='color:#da3633;'>ANOMALY: {alert}</h3>"
                                     f"<p>Критическое изменение в структурах ядра!</p>")
            self.desc_browser.append(f"<b style='color:#da3633;'>[ALERT]</b> Обнаружена аномалия {alert}")

        self.update_3d_candles()

    def start_pipe_listener(self):
        def listen():
            while True:
                if os.path.exists(PIPE_PATH):
                    try:
                        with open(PIPE_PATH, "r") as fifo:
                            while True:
                                line = fifo.readline()
                                if line:
                                    parts = line.strip().split("\t")
                                    if len(parts) == 5:
                                        self.data_received.emit(parts)
                                else: break
                    except: pass
                time.sleep(0.1)

        self.data_received.connect(self.handle_new_data)
        threading.Thread(target=listen, daemon=True).start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NetworkScanApp()
    window.show()
    sys.exit(app.exec_())