import requests
import urllib
import base64
# import json
import time
import plotter


router_addr = '192.168.0.1'
router_passwd = b'karaluch'
api_get_url = 'http://'+router_addr+'/goform/goform_get_cmd_process'
api_set_url = 'http://'+router_addr+'/goform/goform_set_cmd_process'
headers = { 'Referer': 'http://'+router_addr+'/index.html', 'Connection': 'keep-alive' }
session = None
band_lock = 0

def login():
    data = urllib.parse.urlencode({'isTest': 'false', 'goformId': 'LOGIN', 'password': base64.b64encode(router_passwd)})
    result = session.post(api_set_url, headers=headers, data=data)
    if result.status_code == 200:
        print('# login OK:', result.content)
        return True
    else:
        print('login error', result.status_code, result.content)
    return False

def syslog_remote():
    # http://192.168.0.1/goform/zte_syscmd_process?syscmd=zte_syslog&syscall=set_remotelog&action=enable
    result = session.post('http://192.168.0.1/goform/zte_syscmd_process?syscmd=zte_syslog&syscall=set_remotelog&action=enable', headers=headers)
    print('syslog remote:', result.status_code, result.content)

def factory_mode():
    result = session.post('http://192.168.0.1/goform/goform_process?goformId=MODE_SWITCH&switchCmd=FACTORY', headers=headers)
    print('factory mode:', result.status_code, result.content)

def connect():
    data = urllib.parse.urlencode({'isTest': 'false', 'goformId': 'CONNECT_NETWORK', 'notCallback': 'true'})
    result = session.post(api_set_url, headers=headers, data=data)
    if result.status_code == 200:
        print('# connect OK:', result.json())
    else:
        print('connect error', result.status_code, result.json())

def disconnect():
    data = urllib.parse.urlencode({'isTest': 'false', 'goformId': 'DISCONNECT_NETWORK', 'notCallback': 'true'})
    result = session.post(api_set_url, headers=headers, data=data)
    if result.status_code == 200:
        print('# disconnect OK:', result.json())
    else:
        print('disconnect error', result.status_code, result.json())

def usb_modeswitch(mode):
    # https://github.com/zetxx/router-rpi-4G/blob/master/zte-mf-823-cmd.md
    # USB_MODE_SWITCH&usb_mode=N
    # http://192...../goform/goform_set_cmd_process?goformId=USB_MODE_SWITCH&usb_mode=N

        # MSD - USB Mass Storage Device

        # N=0 - PID = 0016: ZTE download mode. AT +ZCDRUN=E.
        # N=1 - PID = 1125: MSD AT +ZCDRUN=9
        # N=2 - PID = 2004: ?.
        # N=3 - PID = 1403: RNDIS + MSD AT +ZCDRUN=8
        # N=4 - PID = 1403: > N=3.
        # N=5 - PID = 1405: > N=3, +CDC/ECM -RNDIS
        # N=6 - PID = 1404: RNDIS + diagnostic port + 2 command ports + MSD + ADB (MF8230ZTED010000).
        # N=7 - PID = 1244: CDC + diagnostic port + 2 command ports + MSD + ADB (MF8230ZTED010000).
        # N=8 - PID = 1402: diagnostic port + 2 command ports + WWAN + MSD + ADB (1234567890ABCDEF).
        # N=9 - PID = 9994: MBIM + diagnostic port + 2 command ports + ADB (1234567890ABCDEF).
    data = urllib.parse.urlencode({'isTest': 'false', 'goformId': 'USB_MODE_SWITCH', 'usb_mode': str(mode)})
    result = session.post(api_set_url, headers=headers, data=data)
    print('mode switch:', result.content)

def set_lte_band_lock(band_id):
    if band_id == 'ANY':
        band_value = 0
    else:
        band_value = 0
        for bid in band_id.split('+'):
            band_value += pow(2, int(bid)-1)
    set_lte_band_mask(band_value)

def set_lte_band_mask(band_mask):
    if band_mask == 0 or band_mask == 0x1a000000000:
        band_mask = 0x1a0080908df

    print('locking band to', hex(band_mask))

    # 0x1	LTE Band 1 2100MHz (O)
    # 0x4	LTE Band 3 1800MHz (O)
    # 0x10	LTE Band 5 850MHz
    # 0x40	LTE Band 7 2600MHz (O)
    # 0x80	LTE Band 8 900MHz
    # 0x80000	LTE Band 20 800MHz (O)
    # 0x7FFFFFFFFFFFFFFF	Any frequency band

    data = urllib.parse.urlencode({'isTest': 'false', 'goformId': 'SET_NETWORK_BAND_LOCK', 'lte_band_lock': hex(band_mask)})
    result = session.post(api_set_url, headers=headers, data=data)
    if result.status_code == 200:
        print('# band lock set OK:', result.content)
    else:
        print('band lock set error', result.status_code, result.content)

def update_band_lock(band, lock):
    global band_lock
    if lock == True:
        band_lock |= pow(2, band-1)
    else:
        band_lock ^= pow(2, band-1)
    print('new band lock mask:', hex(band_lock))
    set_lte_band_mask(0x1a000000000 | band_lock)


def get_lte_info():
    cmd = ','.join(['loginfo', 'rmcc', 'rmnc', 'cell_id', 'lte_band','wan_active_band', 'wan_active_channel', 'network_type', 'lte_band_lock','lte_ca_pcell_band', 'lte_rssi', 'lte_rsrq', 'lte_rsrp', 'lte_snr', 'lte_ca_pcell_band',
    'lte_pci', 'lac_code', 'battery_value', 'realtime_rx_thrpt', 'realtime_tx_thrpt', 'ppp_status'])
    params = {
        'isTest': 'false',
        'cmd': cmd,
        'multi_data': '1',
        '_': str(int(time.time()*1000.0))
    }
    result = session.get(api_get_url, headers=headers, params=params, timeout=(0.2, 1)).json()
    if result['cell_id'] != '':
        result['cell_id'] = str(int(result['cell_id'], 16))
    if result['lac_code'] != '':
        result['lac_code'] = str(int(result['lac_code'], 16))
    if result['realtime_rx_thrpt'] != '':
        result['realtime_rx_thrpt'] = str(int(result['realtime_rx_thrpt'])/102400 -100)
    if result['realtime_tx_thrpt'] != '':
        result['realtime_tx_thrpt'] = str(int(result['realtime_tx_thrpt'])/102400 -100)
    # if result['wan_active_band'] != '':
    #     result['wan_active_band'] = result['wan_active_band'][9:]
    return result

def get_device_info():
    # cmd = ','.join(['ConnectionMode'])
    # cmd = ','.join(['hardware_version', 'wa_inner_version', 'network_provider', ])

    cmd = 'Language,cr_version,wa_inner_version,cr_inner_version,wa_inner_version_tmp,integrate_release_version,integrate_version,wa_version,wa_version_tmp,modem_model,web_version'
    # cmd = 'modem_main_state,pin_status,opms_wan_mode,opms_wan_auto_mode,loginfo,new_version_state,current_upgrade_state,is_mandatory,ppp_dial_conn_fail_counter'

    params = {
        'isTest': 'false',
        'cmd': cmd,
        'multi_data': '1',
        '_': str(int(time.time()*1000.0))
    }
    result = session.get(api_get_url, headers=headers, params=params).json()
    return result

def get_device_diag():
    params = {
        'isTest': 'false',
        'cmd': 'device_diagnnostics',
    }
    return session.get(api_get_url, headers=headers, params=params).json()

# login()
# print(get_device_diag())
# # syslog_remote()
# # usb_modeswitch(6)
# # print("#", get_device_info())
# # print("#", get_lte_info())
# # connect()
# # set_lte_band_lock('7') # best
# set_lte_band_lock('ANY')

# import time
# import sys

plots = [
    ('lte_snr', 'g'),
    ('lte_rsrq', 'y'),
    ('lte_rsrp', 'm'),
    ('lte_rssi', 'r'),
    ('lte_band', 'w'),
    ('realtime_rx_thrpt', 'g'),
    ('realtime_tx_thrpt', 'c')
]


def format_data(lte_info):
        if lte_info['loginfo'] == '':
            login()
            lte_info = get_lte_info()

        if lte_info['network_type'] == 'NO_SERVICE':
            connect()
        elif lte_info['network_type'] == 'LIMITED_SERVICE_LTE':
            if lte_info['lte_band_lock'] != '0x1a0080908df':
                set_lte_band_lock('ANY')

        print('#', lte_info)
        values = []
        values.append('cell_id'+":"+lte_info['cell_id'])
        values.append('battery_value'+":"+lte_info['battery_value'])
        for name, _ in plots:
            values.append(name+":"+lte_info[name])
        values.append("\r\n")
        data = ' '.join(values)
        return data


class StateChange:
    def __init__(self, id):
        self.id = id
    def __call__(self, state):
        update_band_lock(self.id, state!=0)

class CmdWrapper:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args
    def __call__(self):
        if self.args and len(self.args)>0:
            self.cmd(self.args)
        else:
            self.cmd()


def main():
    # from PyQt5 import QtWidgets, QtGui, QtCore  # Should work with PyQt5 / PySide2 / PySide6 as well
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets, QtGui, QtCore

    global session
    # app = plotter.init(plots, get_data, 1000)

    # signal.signal(signal.SIGINT, signalHandler)
    # try:
    #     signal.signal(signal.SIGQUIT, signalHandler)
    # except AttributeError:
    #     pass
    # # signal.signal(signal.SIGKILL, signalHandler)
    # signal.signal(signal.SIGTERM, signalHandler)

    app = QtWidgets.QApplication([])

    ## Define a top-level widget to hold everything
    w = QtWidgets.QWidget()
    w.setWindowTitle('ZTE LTE Modem monitor')
    w.setWindowIcon(QtGui.QIcon("ZTE.png"))

    ## Create some widgets to be placed inside
    labels = []
    lb = (QtWidgets.QLabel('Status:'), QtWidgets.QLabel('Connectiong...'))
    status_label = lb[1]
    labels.append(lb)
    lb = (QtWidgets.QLabel('Network:'), QtWidgets.QLabel('--'))
    net_label = lb[1]
    labels.append(lb)
    lb = (QtWidgets.QLabel('Cell Id:'), QtWidgets.QLabel('--'))
    cell_id_label = lb[1]
    labels.append(lb)
    lb = (QtWidgets.QLabel('Info:'), QtWidgets.QLabel('--'))
    info_label = lb[1]
    labels.append(lb)

    buttons = []
    btn_connect = QtWidgets.QPushButton('Connect')
    btn_connect.clicked.connect(CmdWrapper(connect))
    buttons.append(btn_connect)

    btn_factory = QtWidgets.QPushButton('Factory mode')
    btn_factory.clicked.connect(CmdWrapper(factory_mode))
    buttons.append(btn_factory)

    btn_usb6 = QtWidgets.QPushButton('Usb mode 6')
    btn_usb6.clicked.connect(CmdWrapper(usb_modeswitch, 6))
    buttons.append(btn_usb6)
    # btn_connect = QtWidgets.QPushButton('Reset')
    # btn_connect.clicked.connect(CmdWrapper(reset))
    band_boxes = []

    class StateChange:
        def __init__(self, id):
            self.id = id
        def __call__(self, state):
            update_band_lock(self.id, state!=0)

    for band_id in [1, 3, 7, 20 ,28]:
        band_name = 'B'+str(band_id)
        bbox = QtWidgets.QCheckBox(band_name)
        band_boxes.append(bbox)
        bbox.stateChanged.connect(StateChange(band_id,))

    # btn1 = QtWidgets.QPushButton('Band 1')
    # btn1 = QtWidgets.QPushButton('Band 3')
    # btn1 = QtWidgets.QPushButton('press me')
    # text = QtWidgets.QLineEdit('enter text')
    # listw = QtWidgets.QListWidget()
    plot = plotter.init(plots) ## pg.PlotWidget()

    ## Create a grid layout to manage the widgets size and position
    layout = QtWidgets.QGridLayout()
    w.setLayout(layout)

    ## Add widgets to the layout in their proper positions
    # layout.addLayout(label_layout, 0, 0, 20, 20)
    col = 1
    for lbl in labels:
        layout.addWidget(lbl[0], 0, col)
        layout.addWidget(lbl[1], 0, col+1)
        col+=2
    idx = 1
    for btn in buttons:
        layout.addWidget(btn, idx, 0)
        idx+=1
    layout.addWidget(btn_connect, 1, 0)  # button goes in upper-left
    # layout.addWidget(label, 0, 1)  # button goes in upper-left
    for bb in band_boxes:
        layout.addWidget(bb, idx, 0)
        idx+=1

    # layout.addWidget(text, 1, 0)  # text edit goes in middle-left
    # layout.addWidget(listw, 2, 0)  # list widget goes in bottom-left
    layout.addWidget(plot, 1, 1, 20, 20)  # plot goes on right side, spanning 3 rows
    ## Display the widget as a new window
    w.show()

    session = requests.Session()
    # login()

    def update_plot_data():
        try:
            lte_info = get_lte_info()
            status_label.setText('OK')
            cell_id_label.setText(lte_info['cell_id'])
            info_label.setText(lte_info['wan_active_band'])
            net_label.setText(lte_info['network_type'])
            plotter.update_data(format_data(lte_info).encode())
        except requests.exceptions.ConnectionError:
            status_label.setText("Connection ereror")

    timer1 = QtCore.QTimer()
    timer1.timeout.connect(update_plot_data)
    timer1.start(500)

    app.exec()
    session.close()

if __name__ == '__main__':
    main()
