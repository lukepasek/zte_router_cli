import base64
import hashlib
import requests
import sys

router_ip = '192.168.0.1'
password = b'karaluch'

# password_encoded = hashlib.sha256(base64.b64encode(password.encode())).hexdigest().upper()
password_encoded = base64.b64encode(password)

headers = {'Referer': f'http://{router_ip}/index.html'}
login = requests.post(f'http://{router_ip}/goform/goform_set_cmd_process', data={'goformId': 'LOGIN', 'password': password_encoded}, headers=headers)
if login.json()['result'] == '0':
	ltebandlock=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_band_lock', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	Z_SINR=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'Z_SINR', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	Z_eNB_id=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'Z_eNB_id', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	Z_rsrq=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'Z_rsrq', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	rssi=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'rssi', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	rscp=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'rscp', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_rsrp=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_rsrp', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_pcell_band=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_pcell_band', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_pcell_bandwidth=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_pcell_bandwidth', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_scell_band=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_scell_band', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_scell_bandwidth=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_scell_bandwidth', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_pcell_arfcn=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_pcell_arfcn', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_scell_arfcn=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_scell_arfcn', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	lte_ca_scell_info=requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'lte_ca_scell_info', 'isTest': 'false'}, headers=headers, cookies=login.cookies).json()
	print('Bands hex', ':', ltebandlock['lte_band_lock'])
	print('Active Bands', ':')
	print(('	B'+lte_ca_pcell_band['lte_ca_pcell_band']),' ',lte_ca_pcell_bandwidth['lte_ca_pcell_bandwidth'], ' Mhz (Primary)' )
	secondary_bands=lte_ca_scell_info['lte_ca_scell_info'].split(';')
	for x in secondary_bands:
		banda=x.split(',')
		if len(banda) > 2:
			print(('	B'+banda[2]),banda[4], ' Mhz' )
	print('Cell_ID', ':', Z_eNB_id['Z_eNB_id'])
	cell_ID=int(Z_eNB_id['Z_eNB_id'])
	eNB_ID=int(cell_ID/256)
	sector_ID=cell_ID - eNB_ID*256
	print('eNB_id', ' : ', eNB_ID)
	print('sector_ID', ' : ', sector_ID)
	print('Z_SINR', ':', Z_SINR['Z_SINR'])
	print('Z_rsrq', ':', Z_rsrq['Z_rsrq'])
	print('rssi', ':', rssi['rssi'])
	print('rscp', ':', rscp['rscp'])
	print('lte_rsrp', ':', lte_rsrp['lte_rsrp'])
	print('lte_ca_pcell_band', ':', lte_ca_pcell_band['lte_ca_pcell_band'])
	print('lte_ca_pcell_bandwidth', ':', lte_ca_pcell_bandwidth['lte_ca_pcell_bandwidth'])
	print('lte_ca_scell_band', ':', lte_ca_scell_band['lte_ca_scell_band'])
	print('lte_ca_scell_bandwidth', ':', lte_ca_scell_bandwidth['lte_ca_scell_bandwidth'])
	print('lte_ca_pcell_arfcn', ':', lte_ca_pcell_arfcn['lte_ca_pcell_arfcn'])
	print('lte_ca_scell_arfcn', ':', lte_ca_scell_arfcn['lte_ca_scell_arfcn'])
	print('lte_ca_scell_info', ':', lte_ca_scell_info['lte_ca_scell_info'])
else:
	print(f'Login error: {login.text}')
