import sys
import os
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QPushButton, QGroupBox, QLabel)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Путь к нашему каналу
PIPE_PATH = "/tmp/lkim_telemetry.fifo"

# --- СТИЛИЗАЦИЯ (QSS) ---
STYLE_SHEET = """
QMainWindow { background-color: #0d1117; }
QGroupBox { 
    color: #58a6ff; 
    border: 1px solid #30363d; 
    border-radius: 10px; 
    margin-top: 10px; 
    font-weight: bold; 
}
QPushButton {
    background-color: #238636;
    color: white;
    border-radius: 8px;
    padding: 10px;
    font-weight: bold;
}
QPushButton:hover { background-color: #2ea043; }
QTextBrowser { 
    background-color: #161b22; 
    border: none; 
    color: #c9d1d9; 
    border-radius: 5px; 
}
"""

class NetworkScanApp(QMainWindow):
    # Сигнал для передачи данных из потока чтения в UI
    data_received = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LKIM: Network & Integrity 3D Monitor")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(STYLE_SHEET)

        # Данные для графика
        self.timestamps = []
        self.tx_data = []
        self.rx_data = []
        self.colors = []

        self.setup_ui()
        self.start_pipe_listener()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- ЛЕВАЯ ЧАСТЬ: 3D ГРАФИК ---
        self.fig = Figure(facecolor='#0d1117')
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#0d1117')
        
        main_layout.addWidget(self.canvas, stretch=3)

        # --- ПРАВАЯ ЧАСТЬ: ИНСПЕКТОР ---
        right_panel = QVBoxLayout()
        
        inspector_box = QGroupBox("Integrity Inspector")
        inspector_layout = QVBoxLayout()
        self.inspector_text = QTextBrowser()
        self.inspector_text.setHtml("<h3>Система готова</h3><p>Ожидание данных от Bash-бэкенда...</p>")
        inspector_layout.addWidget(self.inspector_text)
        inspector_box.setLayout(inspector_layout)
        
        right_panel.addWidget(inspector_box)

        # Кнопки
        btn_stop = QPushButton("Остановить мониторинг")
        btn_stop.setStyleSheet("background-color: #da3633;") # Красная кнопка
        right_panel.addWidget(btn_stop)

        main_layout.addLayout(right_panel, stretch=1)

    def update_3d_plot(self, data_list):
        """Отрисовка 3D свечей: TX вверх, RX вниз"""
        # data_list: [timestamp, tx, rx, score, alert_id]
        _, tx, rx, score, alert_id = data_list
        
        self.ax.clear()
        self.ax.set_facecolor('#0d1117')
        
        # Пример логики свечи: TX (Исходящий) - Зеленый столбец вверх
        # RX (Входящий) - Синий/Красный столбец вниз
        x = np.arange(len(self.tx_data))
        y_tx = np.array(self.tx_data)
        y_rx = -np.array(self.rx_data) # Зеркально вниз

        color = '#238636' if int(score) > 80 else '#da3633'
        
        # Рисуем 3D бары
        self.ax.bar3d(x, np.zeros(len(x)), np.zeros(len(x)), 0.5, 0.5, y_tx, color='#2ea043', alpha=0.8)
        self.ax.bar3d(x, np.zeros(len(x)), np.zeros(len(x)), 0.5, 0.5, y_rx, color=color, alpha=0.8)

        self.ax.set_xlabel('Time', color='white')
        self.ax.set_zlabel('Traffic KB/s', color='white')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.tick_params(axis='z', colors='white')

        self.canvas.draw()

    def start_pipe_listener(self):
        """Запуск фонового потока для чтения FIFO"""
        def listen():
            if not os.path.exists(PIPE_PATH):
                return
            
            # Открываем канал
            with open(PIPE_PATH, "r") as fifo:
                while True:
                    line = fifo.readline()
                    if line:
                        parts = line.strip().split("\t")
                        if len(parts) == 5:
                            self.data_received.emit(parts)

        self.data_received.connect(self.handle_new_data)
        threading.Thread(target=listen, daemon=True).start()

    def handle_new_data(self, data):
        # Добавляем данные в массивы
        self.tx_data.append(float(data[1]))
        self.rx_data.append(float(data[2]))
        
        # Ограничиваем количество свечей на экране (например, последние 20)
        if len(self.tx_data) > 20:
            self.tx_data.pop(0)
            self.rx_data.pop(0)

        self.update_3d_plot(data)
        
        # Обновляем инспектор, если есть аномалия
        if data[4] != "NONE":
            self.inspector_text.setHtml(f"<h3 style='color: #da3633;'>ALERT: {data[4]}</h3>"
                                       f"<p>Обнаружена подозрительная активность в ядре!</p>"
                                       f"<p>Integrity Score: {data[3]}%</p>")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NetworkScanApp()
    window.show()
    sys.exit(app.exec_())