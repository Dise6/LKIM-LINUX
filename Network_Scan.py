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

        self.cycle_minutes = 5  # Настройка пользователя
        self.start_session_time = time.time()

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
            try:
                _, tx, rx, score, alert = data
                tx, rx, score = float(tx), float(rx), int(score)
            except (ValueError, TypeError):
                continue
        # Настройка геометрии свечи
        width = 0.7  # Ширина по оси X
        depth = 0.7  # Глубина по оси Y (вот это дает объем!)
            
         # Центрируем свечу по оси Y (чтобы она стояла посередине "дорожки")
        y_pos = (1.0 - depth) / 2
        x_pos = i + (1.0 - width) / 2

        # --- ТЕЛО СВЕЧИ (3D ПАРАЛЛЕЛЕПИПЕД) ---
            
        # RX (Входящий) - Желтый столб вверх
        # bar3d(x, y, z, dx, dy, dz)
        if rx > 0:
            self.ax.bar3d(x_pos, y_pos, 0, width, depth, rx, 
                 color='#ffd700', alpha=0.9, shade=True, edgecolor='#1a1f26')
            
        # TX (Исходящий) - Зеленый столб вниз
        if tx > 0:
            self.ax.bar3d(x_pos, y_pos, 0, width, depth, -tx, 
                color='#00ff41', alpha=0.9, shade=True, edgecolor='#1a1f26')

        # --- ФИТИЛИ АНОМАЛИЙ (Тонкие 3D колонны) ---
        if score > 0:
            wick_w = 0.15 # Очень тонкий
            wick_y = (1.0 - wick_w) / 2
            wick_x = i + (1.0 - wick_w) / 2
                
            # Фитиль RX (Красный лазер вверх)
            wick_len = rx * 0.8 + 200 # Длина зависит от силы аномалии
            self.ax.bar3d(wick_x, wick_y, rx, wick_w, wick_w, wick_len, 
                              color='red', alpha=1.0, shade=False)
                
            # Фитиль TX (Красный лазер вниз)
            self.ax.bar3d(wick_x, wick_y, -tx, wick_w, wick_w, -(tx * 0.8 + 200), 
                            color='red', alpha=1.0, shade=False)
        self.ax.view_init(elev=20, azim=-35)
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
    
    def update_3d_candles(self):
        self.ax.clear()
        # Темный фон графика
        self.ax.set_facecolor('#0b0e14') 
        
        # ПРОВЕРКА ЦИКЛА (очистка графика каждые N минут)
        elapsed = time.time() - self.start_session_time
        if elapsed > (self.cycle_minutes * 60):
            self.history.clear()
            self.start_session_time = time.time()
            self.desc_browser.append("<b style='color:#58a6ff;'>[SYSTEM]</b> Цикл завершен. График сброшен.")
        
        # --- ОТРИСОВКА КРАСНЫХ ЗОН (ЛИМИТЫ) ---
        # Создаем плоскости "потолка" и "пола"
        # X от 0 до 40 (размер буфера), Y от 0 до 1
        limit_val = 800 # Высота, где начинается красная зона (KB/s)
        
        # Сетка для плоскости
        xx, yy = np.meshgrid(range(41), [0, 1])
        
        # Верхняя зона опасности (полупрозрачный красный)
        self.ax.plot_surface(xx, yy, np.full_like(xx, limit_val), alpha=0.1, color='red')
        # Нижняя зона опасности
        self.ax.plot_surface(xx, yy, np.full_like(xx, -limit_val), alpha=0.1, color='red')

        if not self.history:
            self.canvas.draw()
            return

        for i, data in enumerate(self.history):
            _, tx, rx, score, _ = data
            tx, rx = float(tx), float(rx)
            score = float(score) # 0 - норма, >0 - аномалия
            
            # --- ТЕЛО СВЕЧИ (Основной трафик) ---
            # RX (Входящий) - ВВЕРХ (Желтый/Золотой)
            # TX (Исходящий) - ВНИЗ (Зеленый/Матричный)
            
            thickness = 0.6 
            offset = (1.0 - thickness) / 2
            
            # RX Bar (Positive Z)
            self.ax.bar3d(i + offset, offset, 0, thickness, thickness, rx, 
                          color='#ffd700', alpha=0.9, shade=True, edgecolor='#1a1f26')
            
            # TX Bar (Negative Z)
            self.ax.bar3d(i + offset, offset, 0, thickness, thickness, -tx, 
                          color='#00ff41', alpha=0.9, shade=True, edgecolor='#1a1f26')

            # --- ФИТИЛИ АНОМАЛИЙ (The Wicks) ---
            # Рисуем только если есть score (аномалия)
            if score > 0:
                wick_thickness = 0.1
                wick_offset = (1.0 - wick_thickness) / 2
                
                # Длина фитиля зависит от score. 
                # Если score=1, фитиль добавляет 50% длины.
                wick_len_rx = rx * 0.5 * score + 100 # +100 чтобы было видно даже на мелком трафике
                wick_len_tx = tx * 0.5 * score + 100
                
                # RX Wick (Торчит вверх из тела свечи)
                self.ax.bar3d(i + wick_offset, wick_offset, rx, 
                              wick_thickness, wick_thickness, wick_len_rx,
                              color='#ff0000', alpha=1.0) # Ярко-красный
                
                # TX Wick (Торчит вниз из тела свечи)
                self.ax.bar3d(i + wick_offset, wick_offset, -tx, 
                              wick_thickness, wick_thickness, -wick_len_tx,
                              color='#ff0000', alpha=1.0)

        # Настройка камеры и осей
        self.ax.set_zlim(-1200, 1200) # Лимиты оси Z
        self.ax.set_ylim(0, 1)
        self.ax.set_xlim(0, 40)
        
        # Убираем оси для чистого UI
        self.ax.axis('off')
        
        # Можно добавить подписи осей вручную через text, если нужно
        # self.ax.text2D(0.05, 0.95, "TRAFFIC MONITOR", transform=self.ax.transAxes, color="white")

        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NetworkScanApp()
    window.show()
    sys.exit(app.exec_())