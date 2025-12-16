#!/bin/bash

#Функция для сбора дыннх module.sh
collect_module_data() {
	local OUTPUT_FILE="$1"

	#1  Считываем /proc/modules и загружаем список загруженных модулей в файл.
	cat /proc/modules > "$OUTPUT_FILE"

	logger.log "MODULE" "Список модулей ядра сохранен в $OUTPUT_FILE"
}
#Функция проверки
run_check_modules() {
	logger.log "MODULE" "Начало проверки модуля ядра..."

	local BASELINE_FILE="$baseline/modules.bl"
	local TEMP_CURRENT_FILE="$temp/lkim_current_modules.tmp"

	if [[ ! -f "$BASELINE_FILE" ]]; then
		logger.log "MODULES" "Эталонный файл $BASELINE_FILE не найден. Невозможно выполнить проверку."
		return 1
	fi

	#1 Получаем текущие состояние в temp-файл

	cat /proc/modules > "$TEMP_CURRENT_FILE"

	# 2 Сравниваем текущие состояние с baseline с помощью 'diff'
	# diff -U 0 -w -Сравнить файлы, игнорируя пробелы, без контекста.
	# grep '^\+' - Найти только строки, добавленные в текущем файле (Новые модули)
	# grep '^-' - Найти только строки, отсутствующие в текущем файле (Удаленные модули)

	local NEW_MODULES=$(diff -u -w "$BASELINE_FILE" "$TEMP_CURRENT_FILE" | grep '^\+' | grep -v '^\+\+\+')
	local REMOVED_MODULES=$(diff -u -w "$BASELINE_FILE" "$TEMP_CURRENT_FILE" | grep '^-' | grep -v '^\-\-\-')

	# Формируем отчет (логирование)

	if [[ -n "$NEW_MODULES" ]]; then
		logger.log "ALERT" "Обнаружены НОВЫЕ модули ядра (потенциально rootkit): $NEW_MODULES"
	fi

	if [[ -n "$REMOVED_MODULES" ]]; then
		logger.log "WARNING" "Обнаружены УДАЛЕННЫЕ/ИСПАРЯЮЩИЕСЯ модули: $REMOVED_MODULES"
	fi

	if [[ -z "$NEW_MODULES" ]] && [[ -z "REMOVED_MODULES" ]]; then
		logger.log "MODULES" "Целостность модулей ядра потверждена. Различий нет."
	fi

	rm -f "$TEMP_CURRENT_FILE"
}
