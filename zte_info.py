import base64
import hashlib
import requests

router_ip = '192.168.0.1'
password = 'karaluch'



password_encoded = hashlib.sha256(base64.b64encode(password.encode())).hexdigest().upper()
headers = {'Referer': f'http://{router_ip}/index.html'}
login = requests.post(f'http://{router_ip}/goform/goform_set_cmd_process', data={'goformId': 'LOGIN', 'password': password_encoded}, headers=headers)
if login.json()['result'] == '0':
    version1 = requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'Language,cr_version,wa_inner_version,cr_inner_version,wa_inner_version_tmp,integrate_release_version,integrate_version,wa_version,wa_version_tmp', 'multi_data': '1'}, headers=headers, cookies=login.cookies).json()
    version2 = requests.get(f'http://{router_ip}/goform/goform_get_cmd_process', params={'cmd': 'modem_main_state,pin_status,opms_wan_mode,opms_wan_auto_mode,loginfo,new_version_state,current_upgrade_state,is_mandatory,ppp_dial_conn_fail_counter', 'multi_data': '1'}, headers=headers, cookies=login.cookies).json()
    version_string = version1['wa_inner_version'] + version1['cr_version']
    print(version1)
    print(version2)
    print(version_string)
else:
    print(f'Login error: {login.text}')




input("Press Enter to continue...")
