import sys
import os
import threading
import time
import random
from collections import deque
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QGroupBox, QLabel, 
                             QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

PIPE_PATH = "/tmp/lkim_telemetry.fifo"

# --- ЦВЕТОВАЯ ПАЛИТРА (Твой стиль) ---
COLOR_BG = '#0b0e14'
COLOR_RX = '#f1e05a'  # Желтый (Входящий - Вверх)
COLOR_TX = '#2ea043'  # Зеленый (Исходящий - Вниз)
COLOR_ANOMALY = '#da3633' # Красный (Зоны)
COLOR_WICK = '#ffffff' # Белый (Фитили)

class NetworkScanApp(QMainWindow):
    data_received = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LKIM | NETWORK TRAFFIC INTERCEPTOR")
        self.setGeometry(50, 50, 1400, 900)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLOR_BG}; }}")
        
        self.cycle_minutes = 5
        self.start_session_time = time.time()
        # Храним: (timestamp, tx, rx, score, alert_id, tx_peak, rx_peak)
        self.history = deque(maxlen=40) 

        self.setup_ui()
        self.start_pipe_listener()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Header
        header = QHBoxLayout()
        title = QLabel(" [ CORE NETWORK TELEMETRY ]")
        title.setStyleSheet("color: #00ff41; font-weight: bold; font-family: 'Consolas';")
        header.addWidget(title)
        header.addStretch()
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("color: #8b949e; font-family: 'Consolas';")
        header.addWidget(self.timer_label)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        # Левая панель (Инспектор)
        self.desc_browser = QTextBrowser()
        self.desc_browser.setStyleSheet("background-color: #0d1117; border: none; color: #c9d1d9; font-family: 'Consolas';")
        splitter.addWidget(self.desc_browser)

        # Центр (3D График)
        self.fig = Figure(facecolor=COLOR_BG)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        splitter.addWidget(self.canvas)

        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)

    def update_3d_candles(self):
        self.ax.clear()
        self.ax.set_facecolor(COLOR_BG)
        
        # Сброс цикла
        if time.time() - self.start_session_time > (self.cycle_minutes * 60):
            self.history.clear()
            self.start_session_time = time.time()

        if not self.history:
            self.canvas.draw()
            return

        # Настройки геометрии свечи
        w = 0.6  # Ширина (по оси X - время)
        d = 0.6  # Глубина (по оси Y - объем)
        anomaly_threshold = 250 # Порог для красных линий

        for i, data in enumerate(self.history):
            # Распаковка (с учетом добавленных пиков для фитилей)
            _, tx, rx, _, _, tx_p, rx_p = data
            
            x_pos = i  # Время идет вправо
            y_pos = -d/2 # Центрируем по глубине
            
            # 1. ЖЕЛТАЯ ЧАСТЬ (RX / Входящий) -> ВВЕРХ
            self.ax.bar3d(x_pos, y_pos, 0, w, d, rx, 
                          color=COLOR_RX, alpha=0.85, shade=True)
            
            # ФИТИЛЬ RX (Белая линия до пика)
            self.ax.plot([x_pos + w/2, x_pos + w/2], [0, 0], [rx, rx_p], 
                         color=COLOR_WICK, linewidth=1, alpha=0.6)

            # 2. ЗЕЛЕНАЯ ЧАСТЬ (TX / Исходящий) -> ВНИЗ
            # bar3d рисует ОТ z. Чтобы росло вниз, начинаем с -tx и рисуем высоту tx
            self.ax.bar3d(x_pos, y_pos, -tx, w, d, tx, 
                          color=COLOR_TX, alpha=0.85, shade=True)
            
            # ФИТИЛЬ TX (Белая линия вниз до пика)
            self.ax.plot([x_pos + w/2, x_pos + w/2], [0, 0], [-tx, -tx_p], 
                         color=COLOR_WICK, linewidth=1, alpha=0.6)

        # 3. КРАСНЫЕ ЗОНЫ АНОМАЛИЙ (Линии-сетки сверху и снизу)
        curr_len = len(self.history)
        if curr_len > 1:
            x_range = np.linspace(0, curr_len, 2)
            y_range = np.linspace(-1, 1, 2)
            X, Y = np.meshgrid(x_range, y_range)
            # Верхняя граница
            self.ax.plot_wireframe(X, Y, np.full_like(X, anomaly_threshold), 
                                   color=COLOR_ANOMALY, alpha=0.3, linewidth=0.5)
            # Нижняя граница
            self.ax.plot_wireframe(X, Y, np.full_like(X, -anomaly_threshold), 
                                   color=COLOR_ANOMALY, alpha=0.3, linewidth=0.5)

        # Настройка камеры: горизонтальный вектор прогрессии (черная стрелка в твоем уме)
        self.ax.view_init(elev=20, azim=-85)
        
        # Убираем лишнее, оставляем только чистый визуал
        self.ax.set_axis_off()
        self.fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        
        self.canvas.draw()

    def handle_new_data(self, data):
        # Приводим к числам
        ts, tx, rx, score, alert = data
        f_tx, f_rx = float(tx), float(rx)
        
        # Генерируем случайный пик для фитиля (10-30% сверху), 
        # так как в базовом мониторе у нас пока только среднее значение
        tx_peak = f_tx + (f_tx * random.uniform(0.1, 0.3))
        rx_peak = f_rx + (f_rx * random.uniform(0.1, 0.3))
        
        self.history.append((ts, f_tx, f_rx, score, alert, tx_peak, rx_peak))
        
        # Обновляем таймер сессии
        elapsed = int(time.time() - self.start_session_time)
        self.timer_label.setText(time.strftime('%H:%M:%S', time.gmtime(elapsed)))
        
        # Вывод в лог
        self.desc_browser.append(f"<span style='color:{COLOR_RX}'>IN: {rx}</span> | <span style='color:{COLOR_TX}'>OUT: {tx}</span>")
        
        self.update_3d_candles()

    def start_pipe_listener(self):
        def listen():
            while True:
                if os.path.exists(PIPE_PATH):
                    try:
                        with open(PIPE_PATH, "r") as fifo:
                            for line in fifo:
                                parts = line.strip().split("\t")
                                if len(parts) >= 4:
                                    self.data_received.emit(parts)
                    except: pass
                time.sleep(0.1)
        
        self.data_received.connect(self.handle_new_data)
        threading.Thread(target=listen, daemon=True).start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NetworkScanApp()
    window.show()
    sys.exit(app.exec_())