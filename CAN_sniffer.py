
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtGui import QColor
from MainWindow import Ui_MainWindow
import queue
import serial
import time
import struct
import numpy as np
import argparse
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROWS = 4
COLS = 16
NUM_SENSORS = 4
TOTAL_PIXELS = ROWS * COLS

SENSORS = ['FL', 'FR', 'RL', 'RR']
CAN_ADDRESS = {'CFG': 0x700, 'FL': 0x710,
               'FR': 0x720, 'RL': 0x730, 'RR': 0x740}


class CAN_Sniffer(QtWidgets.QMainWindow):
    def __init__(self, parent=None, port=None):
        super(CAN_Sniffer, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.serial = None
        self.rcv_buffer = bytearray()
        self.messages = {}

        # Set shapes of data for all IR images
        self.ir_data = {}
        for sensor in SENSORS:
            self.ir_data[sensor] = np.zeros((ROWS, COLS), dtype=np.int16)
            self.ui.irImages[sensor].setShape(ROWS, COLS)

        self.readTimer = QtCore.QTimer()
        self.readTimer.timeout.connect(self.read_data)

        self.uiUpdateTimer = QtCore.QTimer()
        self.uiUpdateTimer.timeout.connect(self.update_ui)
        self.uiUpdateTimer.start(50)

        # self.ui.serialPortSelectPb.clicked.connect(self.on_select_port)
        # self.ui.applyConfigPb.clicked.connect(self.on_apply_config)
        self.setFixedSize(480, 320)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        if port is not None:
            self.connect_to_port(port)

    def update_ui(self):
        # self.ui.dataTable.setUpdatesEnabled(False)
        # for msg_id, row in self.messages.items():
        #     for i in range(10):
        #         item = row[i][1]
        #         if i == 0:
        #             item.setText(f'0x{msg_id:04X}')
        #         elif i == 1:
        #             item.setText(str(row[i][0]))
        #         else:
        #             item.setText(str(row[i][0]))
        #             if row[i][3]:
        #                 item.setBackground(QtGui.QColor(200, 200, 200))
        #             elif row[i][2]:
        #                 item.setBackground(QtGui.QColor(255, 255, 0))
        #             else:
        #                 item.setBackground(QtGui.QColor(255, 255, 255))

        for sensor in SENSORS:
            new_data = np.fliplr(self.ir_data[sensor])
            if (np.max(new_data) > 0):
                self.ui.irImages[sensor].updateData(new_data)

        # self.ui.dataTable.setUpdatesEnabled(True)

    def on_apply_config(self):
        logger.info('Apply config')
        sampling_rate = self.ui.samplingRateCb.currentIndex()
        # Encode enabled rows in a byte
        row_en = 0
        for i in range(4):
            if self.ui.rowEnCb[i].isChecked():
                row_en |= 1 << i
        logger.info(f'Sampling rate: {sampling_rate}, Row enable: {row_en}')
        if self.serial is not None:
            self.sendPacket(struct.pack('<BB', sampling_rate,
                            row_en), CAN_ADDRESS['CFG'])

    def sendPacket(self, data, stdid=CAN_ADDRESS['CFG'], extid=0, ide=0, rtr=0, dlc=None):
        if dlc is None:
            dlc = len(data)
        # extend data to 8 bytes
        data = data.ljust(8, b'\x00')
        packet = struct.pack("<LLBBB8s", stdid, extid, ide, rtr, dlc, data)
        packet = b'SND' + packet
        self.serial.write(packet)

        logger.debug(f'Sent: {packet.hex()}')

    def on_select_port(self):
        import serial.tools.list_ports
        port_list = [
            port.device for port in serial.tools.list_ports.comports()]
        if self.serial is not None:
            self.serial.close()
            self.readTimer.stop()
        port, ok = QtWidgets.QInputDialog.getItem(
            self, 'Select Port', 'Available Serial Ports:', port_list, 0, False)

        if ok and port:
            self.connect_to_port(port)

    def connect_to_port(self, port):
        # self.ui.serialPortSelectPb.setText(port)
        try:
            self.serial = serial.Serial(
                port, 921600, timeout=0, exclusive=True)
            self.readTimer.start(10)
            self.ui.statusbar.showMessage(f'Connected to {port}')
        except serial.SerialException as e:
            self.ui.statusbar.showMessage(str(e))

    def read_data(self):
        while self.serial.in_waiting:
            self.rcv_buffer.extend(self.serial.read(size=1024))

        while b'RCV' in self.rcv_buffer:
            start_idx = self.rcv_buffer.index(b'RCV')
            # 'RCV' length (3) + CanRxMsg struct length (20)
            end_idx = start_idx + 3 + 20

            if len(self.rcv_buffer) >= end_idx:
                msg_data = self.rcv_buffer[start_idx+3:end_idx]
                CanRxMsg = struct.unpack('<LLBBB8sB', msg_data)
                self.update_data(CanRxMsg)
                self.rcv_buffer = self.rcv_buffer[end_idx:]
            else:
                break

    def update_data(self, CanRxMsg):
        std_id, ext_id, ide, rtr, dlc, data, fmi = CanRxMsg

        if ide == 0x00000000:
            msg_id = std_id
        elif ide == 0x00000004:
            msg_id = ext_id
        else:
            logger.warning(f"Unhandled IDE value: 0x{ide:08X}")
            return

        ir_data = struct.unpack('<4h', data[:8])
        ir_data = np.array(ir_data)/10

        # Determine sensor ID from the message ID
        for sensor in SENSORS:
            if CAN_ADDRESS[sensor] <= std_id <= CAN_ADDRESS[sensor] + 0x0F:
                index = std_id - CAN_ADDRESS[sensor]
                column = index % 4 * 4
                row = index // 4
                self.ir_data[sensor][row, column:column+4] = ir_data
                break

        # # Check if the ID already exists in the table
        # if msg_id in self.messages:
        #     row = self.messages[msg_id]
        # else:
        #     # Add a new row to the table
        #     row_position = self.ui.dataTable.rowCount()
        #     self.ui.dataTable.insertRow(row_position)
        #     row = [[msg_id, QtWidgets.QTableWidgetItem(f'0x{msg_id:X}'), False, False],
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # Count
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[0]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[1]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[2]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[3]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[4]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[5]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[6]
        #            [0, QtWidgets.QTableWidgetItem(), True, False],  # data[7]
        #            ]
        #     self.messages[msg_id] = row
        #     for item in row:
        #         self.ui.dataTable.setItem(
        #             row_position, row.index(item), item[1])

        # # Update the count
        # self.messages[msg_id][1][0] += 1

        # # Update the data bytes (B0 to B7)
        # for i in range(8):
        #     old_value = self.messages[msg_id][i+2][0]
        #     new_value = data[i]
        #     self.messages[msg_id][i+2][0] = new_value
        #     self.messages[msg_id][i+2][2] = old_value != new_value
        #     self.messages[msg_id][i+2][3] = i >= dlc

    def closeEvent(self, event):
        if self.serial is not None:
            self.serial.close()
        event.accept()

if __name__ == '__main__':
    import sys
    parser = argparse.ArgumentParser(description='CAN Sniffer')
    parser.add_argument('--port', '-p', type=str, help='Serial port to use')
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    myapp = CAN_Sniffer(port=args.port)
    myapp.show()
    sys.exit(app.exec_())
