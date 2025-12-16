#!/bin/bash

# 1. Подключение Core модулей 

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

source "$SCRIPT_DIR/core/utils.sh"
source "$SCRIPT_DIR/core/logger.sh"
source "$SCRIPT_DIR/core/baseline.sh"

mkdir -p temp

#2. Запуск полной проверки
run_all_checks() {
	logger.log "SYSTEM" "Начало полной проверки системы..."
	# Здесь все модули для проверки 
	if source checks/module.sh 2>/dev/null; then
		run_check_modules
	fi

	if source checks/syscalls.sh 2>/dev/null; then
		run_check_syscalls
	fi

	logger.log "SYSTEM" "Полная проверка завершена"
}

if [[ "$1" == "--save-baseline" ]]; then
		logger.log "SYSTEM" "ЗАПУЩЕНА ПРОЦЕДУРА СОХРАНЕНИЯ ЭТАЛОНА."
		save_current_baseline
		exit 0
elif [[ "$1" == "--run-check" ]]; then
		logger.log "SYSTEM" "ЗАПУЩЕНА ПРОЦЕДУРА ПОЛНОЙ ПРОВЕРКИ СИСТЕМЫ."
		run_all_checks
		exit 0 
else

	#Пользовательский интерфейс UI 
	echo -e "\n--- \033[1;36mLKIM: Linux Kernel Integrity Monitor\033[0m ---"
	echo "--------------------------------------------------------"
	echo -e "\033[1mИСПОЛЬЗОВАНИЕ:\033[0m"
	echo -e "\033[032m./lkim.sh --save-baseline\033[0m\t\t# Сохранение текущего состояния системы как эталон"
	echo -e "\033[33m./lkim.sh --run-check\033[0m\t\t\t# Запуск полной проверки системы (сравнение с эталоном)"
	echo "--------------------------------------------------------"
	exit 1
fi  
