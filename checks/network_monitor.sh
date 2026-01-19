#!/bin/bash

get_network_traffic() {
	# Считываем /proc/net/dev для получения байтов (RX/TX)
	# Предположим, используемый интерфейс eth0 или первый активный 

	local iface=$(ip route | grep default | awk '{print $5}' | head -n 1)

	read rx1 tx1 < <(awk -v dev="$iface" '$1 ~ dev {print $2, $10}' /proc/net/dev)
	sleep 1 
	read rx2 tx2 < <(awk -v dev="$iface" '$1 ~ dev {print $2, $10}' /proc/net/dev)

	local rx_speed=$(( (rx2 - rx1) / 1024 ))
	local tx_speed=$(( (tx2 - tx1) / 1024 ))

	echo "$tx_speed $rx_speed"
}

run_network_telemetry() {
	init_telemetry_pipe

	while true; do
		# 1. Сбор сетевых метрик 
		read tx rx < <(get_network_traffic)

		#2. Получение текущего статуса целостности 
		# В идеале берем переменную из общего цикла lkim.sh 
		local current_score=100
		local alert_mod="NONE"

		#Простая проверка на аномалии в логах для изменения score 
		if grep -q "ALERT" "logs/lkim.log"; then
			current_score=30
			alert_mod="CORE_ANOMALY"
		fi 

		#3. Отправка пакета в Python
		send_telemetry "$tx" "$rx" "$current_score" "$alert_mod"
	done
} 
