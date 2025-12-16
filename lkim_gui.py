import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QTextEdit, QLabel, QGroupBox, QMessageBox
)
from PyQt5.QtCore import QTimer, QCoreApplication

# --- КОНСТАНТЫ ---
LKIM_SCRIPT = "./lkim.sh"
LOG_FILE = "logs/lkim.log"

class LKIMApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Устанавливаем иконку приложения, если она есть
        # self.setWindowIcon(QIcon('path/to/icon.png'))
        
        self.setWindowTitle("LKIM: Linux Kernel Integrity Monitor (GUI)")
        self.setGeometry(100, 100, 800, 600)
        
        # Гарантируем, что скрипт исполняем
        if not os.access(LKIM_SCRIPT, os.X_OK):
            self.show_error_and_exit(f"Ошибка: Скрипт {LKIM_SCRIPT} не имеет прав на выполнение.\nИспользуйте 'chmod +x {LKIM_SCRIPT}' в терминале.")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.process = None # Переменная для хранения запущенного процесса
        
        self.setup_ui()
        self.setup_logging_updater()
        
    def show_error_and_exit(self, message):
        """Отображает критическое сообщение и завершает работу."""
        QMessageBox.critical(self, "Критическая ошибка", message)
        QCoreApplication.quit()

    def setup_ui(self):
        # 1. Секция Кнопок
        button_group = QGroupBox("Управление LKIM")
        button_layout = QHBoxLayout(button_group)
        
        # Кнопка "Сохранить" (зеленая)
        self.save_btn = QPushButton("Сохранить Baseline")
        self.save_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.save_btn.clicked.connect(lambda: self.run_lkim_command("--save-baseline"))
        
        # Кнопка "Проверить" (голубая)
        self.check_btn = QPushButton("Запустить Проверку")
        self.check_btn.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 10px;")
        self.check_btn.clicked.connect(lambda: self.run_lkim_command("--run-check"))
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.check_btn)
        self.layout.addWidget(button_group)
        
        # 2. Секция Логирования
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        # Черный фон, зеленый шрифт, моноширинный шрифт для лучшей читаемости логов
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #0f0; font-family: 'Courier New', monospace; font-size: 10pt; border: 1px solid #444;")
        
        self.layout.addWidget(QLabel("Логи LKIM (Обновляются в реальном времени):"))
        self.layout.addWidget(self.log_area)

    def setup_logging_updater(self):
        """Настраивает таймер для периодического чтения лог-файла."""
        # Инициализируем лог
        if os.path.exists(LOG_FILE):
             self.update_log_display()
        else:
             self.log_area.setText("[SYSTEM] Ожидание первой команды. Лог-файл еще не создан.")

        # Таймер для обновления логов (каждые 300 мс)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log_display)
        self.timer.start(300)

    def run_lkim_command(self, argument):
        """Запускает lkim.sh в отдельном процессе."""
        # Отключаем кнопки, пока идет выполнение, чтобы избежать двойного запуска
        self.save_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        
        self.log_area.append(f"\n[GUI] Запрос на выполнение '{argument}'...")
        
        try:
            # Запуск Bash-скрипта. Вывод в logs/lkim.log.
            self.process = subprocess.Popen([LKIM_SCRIPT, argument],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
            
            # Запускаем таймер, чтобы следить за завершением процесса
            self.check_process_timer = QTimer(self)
            self.check_process_timer.timeout.connect(self.check_lkim_process)
            self.check_process_timer.start(200)

        except Exception as e:
            self.log_area.append(f"[GUI ERROR] Не удалось запустить скрипт: {e}")
            self.save_btn.setEnabled(True)
            self.check_btn.setEnabled(True)
    
    def check_lkim_process(self):
        """Проверяет, завершился ли запущенный процесс lkim.sh."""
        if self.process and self.process.poll() is not None:  # Процесс завершился
            self.check_process_timer.stop()
            
            self.process.communicate() # Считываем оставшийся вывод, чтобы избежать зависания
            
            if self.process.returncode != 0:
                self.log_area.append(f"[GUI ALERT] Скрипт завершился с ошибкой (код {self.process.returncode}). Проверьте лог-файл.")
            else:
                self.log_area.append("[GUI] Команда завершена успешно. Финальный отчет в логе.")

            # Включаем кнопки
            self.save_btn.setEnabled(True)
            self.check_btn.setEnabled(True)


    def update_log_display(self):
        """Читает лог-файл и обновляет QTextEdit, автоматически прокручивая его вниз."""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Обновляем только если содержимое изменилось
                if self.log_area.toPlainText() != content:
                    self.log_area.setText(content)
                    # Принудительная прокрутка вниз
                    v_scroll = self.log_area.verticalScrollBar()
                    v_scroll.setValue(v_scroll.maximum())
                    
        except FileNotFoundError:
            pass # Если log_file еще не создан

if __name__ == '__main__':
    # Убедимся, что Python может использовать PyQt5
    try:
        app = QApplication(sys.argv)
        window = LKIMApp()
        window.show()
        sys.exit(app.exec_())
    except ImportError:
         print("Ошибка: Библиотека PyQt5 не найдена. Установите ее: pip install PyQt5")
    except Exception as e:
         print(f"Неизвестная ошибка: {e}")