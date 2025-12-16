#!/bin/bash


get_system_map_file() {

	#Ищет System.map для текущего запущенного ядра
	local KERNEL_VERSION=$(uname -r)
	local SYSTEM_MAP="/boot/System.map-$KERNEL_VERSION"

	if [[ -f "$SYSTEM_MAP" ]]; then
		echo "$SYSTEM_MAP"
	else
		logger.log "WARNING" "Файл System.map для ядра $KERNEL_VERSION не найден в $SYSTEM_MAP."
		return 1
	fi
}

collect_syscalls_data() {

	local OUTPUT_FILE="$1"
	local SYSTEM_MAP_FILE=$(get_system_map_file)

	if [[ -z "$SYSTEM_MAP_FILE" ]]; then
		logger.log "ERROR" "Невозможно собрать данные syscalls: System.map не найден"
		return 1
	fi

	grep ' sys_ ' "$SYSTEM_MAP_FILE" | awk '{print $NF}' > "$OUTPUT_FILE"

	logger.log "SYSCALLS" "Список системных вызово сохранен в $OUTPUT_FILE"

}

run_check_syscalls() {

	logger.log "SYSCALLS" "Начало проверки таблицы системных вызовов..."

	local BASELINE_FILE="baseline/syscalls.bl"

	if [[ ! -f "$BASELINE_FILE" ]]; then
		logger.log "SYSCALLS" "Эталонный файл $BASELINE_FILE не найден. Невозможно выполнить проверк"
		return 1
	fi 

	local TEMP_CURRENT_FILE="temp/lkim_current_syscalls.tmp"
	grep ' sys_ ' /proc/kallsyms | awk '{print $NF}' > "$TEMP_CURRENT_FILE"

	local DIFF_OUTPUT=$(diff -u -w "$BASELINE_FILE" "$TEMP_CURRENT_FILE")

	local NEW_SYSCALLS=$(echo "$DIFF_OUTPUT" | grep '^\+' | grep -v '^\+\+\+')
	local REMOVED_SYSCALLS=$(echo "$DIFF_OUTPUT" | grep '^-' | grep -v '^\-\-\-')

	if [[ -n "$NEW_SYSCALLS" ]]; then
		logger.log "ALERT" "Обнаружены НОВЫЕ системные вызовы (потенциальная инъекция): $NEW_SYSCALLS"
	fi

	if [[ -n "$REMOVED_SYSCALLS" ]]; then
		logger.log "WARNING" "Обнаружены УДАЛЕННЫЕ системные вызовы: $REMOVED_SYSCALLS"

	fi

	if [[ -z  "$NEW_SYSCALLS" ]] && [[ -z "$REMOVED_SYSCALLS" ]]; then
		logger.log "SYSCALLS" "Целостность системных вызовов потверждена. Различий нет"
	fi

	rm -f "$TEMP_CURRENT_FILE"
}
