#!/bin/bash

HISTORY_SIZE=10 #Сколько последних замеров помнить для измерения среднего значения 
ANOMALY_THRESHOLD=2 # во сколько раз превышание считается аномалией (фитиль)

declare -a rx_history
declare -a tx_history

calculate_average() {
	local arr=("$@")
	local sum=0
	local count=${#arr[@]}

	if [[ "$count" -eq 0 ]]; then echo 0; return; fi

	for val in "${arr[@]}"; do
		sum=$((sum + val))
	done 

	echo $((sum /count))
}

get_network_traffic() {
	# Считываем /proc/net/dev для получения байтов (RX/TX)
	# Предположим, используемый интерфейс eth0 или первый активный
	# Автоопределение интерфейса (берем тот, где есть дефолтный роут) 

	local iface=$(ip route | grep default | awk '{print $5}' | head -n 1)

	if [[ -z "$iface" ]]; then iface="eth0"; fi

	read rx1 tx1 < <(awk -v dev="$iface" '$1 ~ dev {print $2, $10}' /proc/net/dev)
	sleep 1 
	read rx2 tx2 < <(awk -v dev="$iface" '$1 ~ dev {print $2, $10}' /proc/net/dev)

	local rx_speed=$(( (rx2 - rx1) / 1024 ))
	local tx_speed=$(( (tx2 - tx1) / 1024 ))

	echo "$tx_speed $rx_speed"
}

run_network_telemetry() {
	init_telemetry_pipe

	logger.log "NETWORK" "Запущен анализ трафика на интерфейсе: $(ip route | grep default | awk '{print $5}')"

	while true; do
		# 1. Сбор сетевых метрик 
		read tx_curr rx_curr < <(get_network_traffic)
		# обнавление истории и расчет среднего (Baseline)
		rx_history+=($rx_curr)
		tx_history+=($tx_curr)
		
		# Ограничение размера истории
		if [[ ${#rx_history[@]} -gt $HISTORY_SIZE ]]; then
			rx_history=("${rx_history[@]:1}")
			tx_history=("${tx_history[@]:1}")
		fi

		rx_avg=$(calculate_average "${rx_history[@]}")
		tx_avg=$(calculate_average "${tx_history[@]}")

		# Расчет коэффициента аномалии (SCORE)
		# Score будет множителем: 0 = норма, 1.0 = превышение в 2 раза,2.0 = в 3 раза и т.д
		# это определяет длину фитиля 

		# зашита от деления на 0 
		[[ $rx_avg -eq 0 ]] && rx_avg=1
		[[ $tx_avg -eq 0 ]] && tx_avg=1

		# Вычисляем превышение (heuristic logic)
		# Если текущие значение > среднего * порог, то score растет
		anomaly_score=0 
	
		if (( tx_curr > tx_avg * ANOMALY_THRESHOLD )) || (( rx_curr > rx_avg * ANOMALY_THRESHOLD )); then
			# Простая формула для демонстрации 
			anomaly_score=1
		fi 

		local alert_mod="NONE"
		if grep -q "ALERT" "logs/lkim.log"; then
			alert_mod="SYSTEM_COMPROMISED"
			anomaly_score=5 # Максимальный фитиль при взломе
		fi

		send_telemetry "$tx_curr" "$rx_curr" "$anomaly_score" "$alert_mod" "NET_SCAN"
	done
} 
