#!/bin/bash

# 1. Подключение Core модулей 

source core/utils.sh
source core/baseline.sh
source core/logger.sh

#2. Запуск полной проверки
run_all_checks() {
	logger.log "SYSTEM" "Начало полной проверки системы..."
	# Здесь все модули для проверки 
	logger.log "SYSTEM" "Полная проверка завершена"

#3. Обработка аргументов
if [[ "$1 == "--save-baseline"]]; then
	save_current_baseline #Функция в core/baseline.sh
	exit 0
elif [[ "$1 =="--run-check ]]; then
	run_all_checks
	exit 0
else
	#Пользовательский интерфейс UI
	echo "--- LKIM: Linux Kernel Integrity Monitor ---"
	echo "Использование:"
	echo " ./lkim.sh --save-baseline # Сохранить текущие состояние как эталон?"
	echo " ./lkim.sh --run-check	  # Запустить полную проверку системы?"
	echo "-------------------------------------------"
	exit 1
fi 
 
