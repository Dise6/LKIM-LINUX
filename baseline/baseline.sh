#!/bin/bash

# Каталог для хранения эталонных данных
BASELINE_DIR="baseline"

#Функция для сохранения данных (Сбор текуших данных со всех проверочных модулей)
save_current_baseline() {
	#1. Проверка существования каталога baseline
	if [[! -d "$BASELINE_DIR" ]]; then
		mkdir -p "BASELINE_DIR"
		logger.log "BASELINE_DIR" "Каталог baseline Создан."
	fi

	logger.log "BASELINE" "Начинается сбор и хранение эталонных данных..."

	#Пример вызова модулей ядра(checks/module.sh)
	if source checks/module.sh 2>/dev/null; then
		collect_module_data "BASELINE_DIR/module.bl"
	else
		logger.log "ERROR" "Не удалось подключить checks/module.sh"
	fi

	logger.log "BASELINE" "Сбор Эталонных данных завершен."

#Функция для загрузки данных baseline (Загрузка эталонного файла в переменную или выводит его.)
load_baseline_data() {
	local BASELINE_FILE="$1"

	if [[ -f "BASELINE_FILE" ]]; then
		#Выводит содержимое файла baseline для последующей обработки модулем checks/*
		cat "BASELINE_FILE"
	else
		logger.log "ERROR" "Эталонный файл не найден: $BASELINE_FILE"
		return 1
	fi
}
