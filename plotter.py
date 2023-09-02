from logging import shutdown
from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import serial
import sys
from bleak import BleakClient, BleakError, exc
from qasync import QEventLoop
import signal
from collections import deque
import time
import asyncio
from aiohttp import web

enableOpenGl = False

if enableOpenGl:
    try:
        import OpenGL
        pyqtgraph.setConfigOption('useOpenGL', True)
        pyqtgraph.setConfigOption('enableExperimental', True)
    except Exception as e:
        print(
            f"Enabling OpenGL failed with {e}. Will result in slow rendering. Try installing PyOpenGL.")

reconnect = True
ble_client = None
close_event = None
ctrl_c_cnt = 0
parser = None
start_time = time.monotonic_ns()
num_samples = 3600
max_range = 1200
serial_port = None
t = deque([])
cnt = -1
sample_frame = None
labels = []
#"vs", "vb", "is", "ib"]
# label_map = {}
# colors = {
#     "vs": 'r',
#     "vb": 'y',
#     "is": 'm',
#     "ib": 'g'
# }
curves = {}
data = {}
plt = None

# app = None
data_changed = False

def initQtApp(plots, buttons=None):
    global plt
# import pyqtgraph as pg
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    app = QtWidgets.QApplication([])
    # app.setWindowIcon(QtGui.QIcon("icon.png"))
    # app.setWindowIcon(QtGui.QIcon("ZTE.png"))
    w = QtWidgets.QWidget()
    w.setWindowTitle('PyQtGraph example')
    w.setWindowIcon(QtGui.QIcon("ZTE.png"))

    btn = QtWidgets.QPushButton('press me')
    text = QtWidgets.QLineEdit('enter text')
    listw = QtWidgets.QListWidget()

    # pg.setConfigOption('antialias', True)
    # pg.setConfigOption('background', "#202020")
    # plt = pg.PlotWidget()
    # # plt = pyqtgraph.plot()
    # plt.clipToView = True
    # plt.autoDownsample = True
    # plt.skipFiniteCheck = True
    # plt.setYRange(-120, 20, padding=0)
    # plt.setXRange(0, max_range, padding=0)
    # plt.showGrid(x=True, y=True, alpha=0.3)
    # plt.addLegend()
    # # plt.resize(800, 600)

    for name, color in plots:
        curve = pg.PlotCurveItem(
            pen=({'color': color, 'width': 1}), skipFiniteCheck=True, name=name)
        # plt.addItem(curve)
        curve.setPos(0, 0)
        curves[name] = curve
        d = deque([])
        data[name] = d
        curve.setData(x=np.array(t, copy=False), y=np.array(d, copy=False))

    # inf1 = pyqtgraph.InfiniteLine(movable=True, angle=0, pen='y', hoverPen=(0, 200, 0), label='{value:0.2f}',
    #                               labelOpts={'color': 'y', 'movable': True, 'fill': (0, 0, 200, 100)})
    # inf1.setPos([0, 0])
    # plt.addItem(inf1)

    layout = QtWidgets.QGridLayout()
    w.setLayout(layout)

    layout.addWidget(btn, 0, 0)  # button goes in upper-left
    layout.addWidget(text, 1, 0)  # text edit goes in middle-left
    layout.addWidget(listw, 2, 0)  # list widget goes in bottom-left
    # layout.addWidget(plt, 0, 1, 3, 1)  # plot goes on right side, spanning 3 rows
    w.show()

    return app


def plot(values):
    global cnt, t, sample_frame, data_changed

    cnt += 1
    data_changed = True
    try:
        ts = values["t"]
    except KeyError:
        ts = (time.monotonic_ns() - start_time)/100000000
    if cnt >= num_samples:
        t.rotate(-1)
        t[-1] = ts
    else:
        t.append(ts)

    for l in labels:
        val = None
        d = data[l]
        if l in values:
            val = values[l]
        else:
            val = 0
        if cnt >= num_samples:
            d.rotate(-1)
            d[-1] = val
        else:
            d.append(val)


class StreamParser:
    EOL = b'\r\n'
    line_buffer = bytearray(1024*8)
    buffer_mem = memoryview(line_buffer)
    buffer_ptr = 0
    buffer_offset = 0
    line_callback = None

    def set_line_callback(self, callback):
        if (callable(callback)):
            self.line_callback = callback

    def __init__(self, callback):
        self.set_line_callback(callback)

    def parse_line(self, line):
        global sample_frame
        values = {}
        tag = bytearray()
        val = bytearray()
        tag_parse = True
        for c in line:
            # sys.stdout.write(chr(c))
            if tag_parse:
                if c == 58:
                    tag_parse = False
                elif c != 32 or c != 9:
                    tag.append(c)
            else:
                if c == 45 or c == 46 or c >= 48 and c <= 57:
                    val.append(c)
                elif c == 32 or c == 9 or c == 10 or c == 13:
                    if len(val) > 0:
                        try:
                            values[tag.decode('ascii')] = float(
                                val.decode('ascii'))
                        except ValueError as e:
                            print("-- Value error - key/value skipped:",
                                  tag, val, line, e)
                    tag.clear()
                    val.clear()
                    tag_parse = True
        # sys.stdout.write('\n')
        # sys.stdout.flush()
        if (len(tag) > 0 and len(val) > 0):
            try:
                values[tag.decode('ascii')] = float(val.decode('ascii'))
            except ValueError:
                pass
        sample_frame = {}
        sample_frame["__ts"] = time.monotonic_ns()
        # for index, (key, value) in enumerate(values):
        # mapped_values = {}
        # for key, value in values.items():
        #     mapped_key = llabel_map.get(key)
        #     if mapped_key != None:
        #         mapped_values[mapped_key] = value
        #     else:
        #         mapped_values[key] = value
        #     sample_frame[key] = value
        return values

    def process_data(self, data):
        sys.stdout.write(data.decode('ascii'))
        sys.stdout.flush()
        eol = self.EOL
        buffer = self.line_buffer
        data_len = len(data)
        mem_offset = self.buffer_ptr
        self.buffer_ptr = self.buffer_ptr+data_len
        dst_mem = self.buffer_mem[mem_offset:self.buffer_ptr]
        dst_mem[:] = data
        if buffer.rfind(eol, self.buffer_offset, self.buffer_ptr) > -1:
            ls = self.buffer_offset
            le = buffer.find(eol, ls, self.buffer_ptr)
            while le > -1:
                if buffer[ls] != 35 and le > ls:
                    line = self.buffer_mem[ls:le]
                    values = self.parse_line(line)
                    if self.line_callback != None:
                        self.line_callback(values)
                ls = le + 2
                le = buffer.find(eol, ls, self.buffer_ptr)
            if ls == self.buffer_ptr:
                self.buffer_ptr = 0
                self.buffer_offset = 0
            else:
                if self.buffer_ptr > (1024*6):
                    left = self.buffer_ptr-self.buffer_offset
                    dst_mem = self.buffer_mem[0:left]
                    dst_mem[:] = self.buffer_mem[self.buffer_offset:self.buffer_ptr]
                    self.buffer_ptr = left
                    self.buffer_offset = 0
                else:
                    self.buffer_offset = ls

    # def append(self, data):
    #     sys.stdout.buffer.write(data)
    #     sys.stdout.buffer.flush()
    #     self.line_buffer.extend(data)
    #     line_src = self.line_buffer
    #     sol_ptr = 0
    #     eol_ptr = line_src.find(self.eol, sol_ptr)
    #     while eol_ptr > -1:
    #         line = line_src[sol_ptr:eol_ptr]
    #         if len(line) > 0 and line[0] != 35:
    #             try:
    #                 values = self.parse_line(line)
    #                 if not self.line_callback == None:
    #                     self.line_callback(values)
    #             except ValueError as e:
    #                 print("-- Value error - line skipped:", line, e)
    #         sol_ptr = eol_ptr + 1
    #         eol_ptr = line_src.find(self.eol, sol_ptr)
    #     if sol_ptr:
    #         self.line_buffer = line_src[sol_ptr:]

    # def append2(self, data):
    #     buffer = self.line_buffer
    #     buffer.extend(data)
    #     if data.rfind(EOL) > -1:
    #         ls = 0
    #         le = buffer.find(EOL)
    #         while le > -1:
    #             if buffer[ls] != 35 and le > ls:
    #                 values = parse_line(buffer, ls, le)
    #                 if not self.line_callback == None:
    #                     self.line_callback(values)
    #             ls = le + 2
    #             le = buffer.find(EOL, ls)
    #         buffer = buffer[ls:]


def poll_serial():
    global serial_port
    if not serial_port and reconnect:
        serial_port = serial.Serial(port, port_speed, timeout=0)
        print("--- Serial port open:", port)
    data = serial_port.read_all()
    while data and len(data) > 0:
        parser.process_data(data)
        data = serial_port.read_all()


async def ble_serial_close():
    if ble_client != None:
        print("--- Closing BLE connection")
        try:
            await ble_client.stop_notify(SERIAL_CHR_UUID)
            await ble_client.disconnect()
        except BleakError as err:
            print("--- BLE connection error:", err)
    else:
        print("--- BLE connection not open")


def ble_disconnect_handler(client):
    print("--- BLE connection disconected")
    if reconnect:
        print("--- BLE connection reconnecting")
        close_event.set()


async def ble_serial_open(address):
    global close_event, ble_client
    close_event = asyncio.Event()

    print("--- Connecting to BLE device", address)
    while not close_event.is_set():
        try:
            ble_client = BleakClient(address, use_cached=False)
            ble_client.set_disconnected_callback(ble_disconnect_handler)
            if await ble_client.connect(timeout=3):
                await ble_client.start_notify(SERIAL_CHR_UUID, lambda i, d: parser.process_data(d))
                print("--- BLE connection open")
                await close_event.wait()
                if reconnect:
                    close_event = asyncio.Event()
        except BleakError as err:
            print("--- BLE connect error:", err)
        except TimeoutError:
            print("--- BLE connect timeout")
        # except GeneratorExit as err:
        #     pass
        except asyncio.CancelledError:
            break
        finally:
            if (ble_client.is_connected == True):
                await ble_serial_close()

close_app = None
close = None


def signalHandler(sig, frame):
    global ctrl_c_cnt
    try:
        print()
        if sig == signal.SIGINT:
            print("--- Exiting on keyboard interrupt")
        else:
            print("--- Exiting on signal", sig)
        if ctrl_c_cnt == 0:
            if close_app != None:
                close_app()
            else:
                close()
        ctrl_c_cnt += 1
        if ctrl_c_cnt > 2:
            print("--- Terminating on repeted signal")
            sys.exit(1)
    except:
        sys.exit(1)


async def handleHttp(request):
    text = ""
    if sample_frame != None:
        ts = sample_frame["__ts"]
        if ts+2000000000 > time.monotonic_ns():
            for key, value in sample_frame.items():
                if key != "__ts":
                    text += "value{name=\""+key+"\", port=\"" + \
                        port+"\"} " + str(value) + "\n"
        else:
            text = "### Data is stale"+"\n"
    else:
        text = "### No valid data sampled or parsed"+"\n"
    return web.Response(text=text)


def initHttpServer(loop):
    http_server = web.Application()
    http_server.router.add_route('GET', '/', handleHttp)
    handler = http_server.make_handler()
    f = loop.create_server(handler, '0.0.0.0', 8585)
    srv = loop.run_until_complete(f)
    return srv


def update_plot():
    global data_changed
    if data_changed and plt != None:
        data_changed = False
        plt.setUpdatesEnabled(False)
        start = t[0]
        end = t[-1]
        if end > max_range:
            plt.setXRange(end-max_range, end, padding=0)
        else:
            plt.setXRange(start, start+max_range, padding=0)
        for l in labels:
            c = curves[l]
            d = data[l]
            c.setData(x=np.array(t, copy=False), y=np.array(d, copy=False))
        plt.setUpdatesEnabled(True)
        plt.update()


def init(plots):
    global plt, parser, labels

    parser = StreamParser(None)
    parser.set_line_callback(plot)

    labels = []

    pg.setConfigOption('antialias', True)
    pg.setConfigOption('background', "#202020")
    plt = pg.PlotWidget()
    # plt = pyqtgraph.plot()
    plt.clipToView = True
    plt.autoDownsample = True
    plt.skipFiniteCheck = True
    plt.setYRange(-120, 20, padding=0)
    plt.setXRange(0, max_range, padding=0)
    plt.showGrid(x=True, y=True, alpha=0.3)
    plt.addLegend()
    # plt.resize(800, 600)

    for name, color in plots:
        labels.append(name)
        curve = pg.PlotCurveItem(
            pen=({'color': color, 'width': 1}), skipFiniteCheck=True, name=name)
        plt.addItem(curve)
        curve.setPos(0, 0)
        curves[name] = curve
        d = deque([])
        data[name] = d
        curve.setData(x=np.array(t, copy=False), y=np.array(d, copy=False))
    return plt

def update_data(src_data):
    print('procesing data: ',src_data)
    # src_data = data_callback()
    # if src_data and src_data != '\n' and src_data[0] != '#':
    parser.process_data(src_data)
    update_plot()

def start_timers(data_callback, interval):
    timer2 = QtCore.QTimer()
    timer2.timeout.connect(update_plot)
    timer2.start(100)

    def poll_data():
        src_data = data_callback()
        if src_data and src_data != '\n' and src_data[0] != '#':
            parser.process_data(src_data.encode())
            # update_plot()

    timer1 = QtCore.QTimer()
    timer1.timeout.connect(poll_data)
    timer1.start(interval)


if __name__ == '__main__':
    init()
