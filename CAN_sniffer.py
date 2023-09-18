
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtGui import QColor
from MainWindow import Ui_MainWindow
import queue
import serial
import time
import struct
import numpy as np
import argparse

ROWS = 4
COLS = 16
TOTAL_PIXELS = ROWS * COLS

SENSORS = ['FL', 'FR', 'RL', 'RR']
CAN_ADDRESS = {'CFG': 0x700, 'FL': 0x710, 'FR': 0x720, 'RL': 0x730, 'RR': 0x740}
 
class CAN_Sniffer(QtWidgets.QMainWindow):
    def __init__(self, parent=None, port=None):
        super(CAN_Sniffer, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.serial = None
        self.rcv_buffer = bytearray()
        self.messages = {}
        self.ir_data = np.zeros((ROWS, COLS), dtype=np.int16)

        # Set shapes of data for all IR images
        for sensor in SENSORS:
            self.ui.irImages[sensor].setShape(ROWS, COLS)

        self.data_q = queue.Queue()
        self.error_q = queue.Queue()
        self.timer = QtCore.QTimer()

        self.timer.timeout.connect(self.read_data)
        self.ui.serialPortSelectPb.clicked.connect(self.on_select_port)
        self.ui.applyConfigPb.clicked.connect(self.on_apply_config)

        if port is not None:
            self.connect_to_port(port)

    def on_apply_config(self):
        print('Apply config')
        sampling_rate = self.ui.samplingRateCb.currentIndex()
        # Encode enabled rows in a byte
        row_en = 0
        for i in range(4):
            if self.ui.rowEnCb[i].isChecked():
                row_en |= 1 << i
        print(f'Sampling rate: {sampling_rate}, Row enable: {row_en}')
        if self.serial is not None:
            self.sendPacket(struct.pack('<BB', sampling_rate, row_en), CAN_ADDRESS['CFG'])

    def sendPacket(self, data, stdid=CAN_ADDRESS['CFG'], extid=0, ide=0, rtr=0, dlc=None):
        if dlc is None:
            dlc = len(data)
        # extend data to 8 bytes
        data = data.ljust(8, b'\x00')
        packet = struct.pack("<LLBBB8s", stdid, extid, ide, rtr, dlc, data)
        packet = b'SND' + packet
        self.serial.write(packet)

        print(f'Sent: {packet.hex()}')


    def on_select_port(self):
        import serial.tools.list_ports
        port_list = [port.device for port in serial.tools.list_ports.comports()]
        if self.serial is not None:
            self.serial.close()
            self.timer.stop()
        port, ok = QtWidgets.QInputDialog.getItem(self, 'Select Port', 'Available Serial Ports:', port_list, 0, False)
        
        if ok and port:
            self.connect_to_port(port)
    
    def connect_to_port(self, port):
        self.ui.serialPortSelectPb.setText(port)
        try:
            self.serial = serial.Serial(port, 921600, timeout=0, exclusive=True)
            self.timer.start(100)
            self.ui.statusbar.showMessage(f'Connected to {port}')
        except serial.SerialException as e:
            self.ui.statusbar.showMessage(str(e))

    def read_data(self):
        while self.serial.in_waiting:
            self.rcv_buffer.extend(self.serial.read(size=1024))
            
        while b'RCV' in self.rcv_buffer:
            start_idx = self.rcv_buffer.index(b'RCV')
            end_idx = start_idx + 3 + 20  # 'RCV' length (3) + CanRxMsg struct length (20)
            
            if len(self.rcv_buffer) >= end_idx:
                msg_data = self.rcv_buffer[start_idx+3:end_idx]
                CanRxMsg = struct.unpack('<LLBBB8sB', msg_data)
                self.update_data(CanRxMsg)
                self.rcv_buffer = self.rcv_buffer[end_idx:]
            else:
                break

    def update_ir_data(self, std_id, new_data):
        for sensor in SENSORS:
            if CAN_ADDRESS[sensor] <= std_id <= CAN_ADDRESS[sensor] + 0x0F:
                index = std_id - CAN_ADDRESS[sensor]
                column = index % 4
                row = index // 4 * 4
                # index = (std_id - CAN_ADDRESS[sensor]) * 4
                new_data = np.array(new_data)/10
                self.ir_data[row, column:column+4] = new_data
                # self.ir_data[index:index + 4] = new_data

    def update_data(self, CanRxMsg):
        t0 = time.time()
        std_id, ext_id, ide, rtr, dlc, data, fmi = CanRxMsg
        new_message = True
        
        if ide == 0x00000000:
            msg_id = std_id
        elif ide == 0x00000004:
            msg_id = ext_id
        else:
            print(f"Unhandled IDE value: 0x{ide:08X}")
            return

        ir_data = struct.unpack('<4h', data[:8])
        ir_data = np.array(ir_data)/10

        # Determine sensor ID from the message ID
        for sensor in SENSORS:
            if CAN_ADDRESS[sensor] <= std_id <= CAN_ADDRESS[sensor] + 0x0F:
                index = std_id - CAN_ADDRESS[sensor]
                column = index % 4 * 4
                row = index // 4
                self.ir_data[row, column:column+4] = ir_data
                break

        # print(f'ID: 0x{msg_id:X}->{sensor}, Data: {ir_data}')
        self.ui.irImages[sensor].updateData(np.fliplr(self.ir_data))

        t1 = time.time()
        row_position = -1
        # Check if the ID already exists in the table
        for row in range(self.ui.dataTable.rowCount()):
            table_id = self.ui.dataTable.item(row, 0).text()
            if table_id == f'0x{msg_id:X}':
                row_position = row
                new_message = False
                break

        # If ID not found, add a new row
        if row_position == -1:
            row_position = self.ui.dataTable.rowCount()
            self.ui.dataTable.insertRow(row_position)
            self.ui.dataTable.setItem(row_position, 0, QtWidgets.QTableWidgetItem(f'0x{msg_id:X}'))
            self.ui.dataTable.setItem(row_position, 1, QtWidgets.QTableWidgetItem("0"))  # Count
            for i in range(8):
                self.ui.dataTable.setItem(row_position, 2 + i, QtWidgets.QTableWidgetItem())
        t2 = time.time()
        # Update the count
        count_item = self.ui.dataTable.item(row_position, 1)
        new_count = int(count_item.text()) + 1
        count_item.setText(str(new_count))
        t3 = time.time()
        # Update the data bytes (B0 to B7)
        data_bytes = CanRxMsg[5]
        for i in range(8):
            new_value = f'{data_bytes[i]:2X}'

            item = self.ui.dataTable.item(row_position, 2 + i)
            old_value = item.text()

            # item = QtWidgets.QTableWidgetItem(new_value)\
            # item = self.ui.dataTable.item(row_position, 2 + i)
            item.setText(new_value)

            if i >= dlc:
                item.setBackground(QtGui.QColor(200, 200, 200))
            elif new_message or new_value != old_value:
                # print(f'New value: {new_value}, Old value: {old_value} @ row: {row_position}, col: {2 + i}')
                item.setBackground(QtGui.QColor(255, 255, 0))
            else:
                item.setBackground(QtGui.QColor(255, 255, 255))
            # self.ui.dataTable.setItem(row_position, 2 + i, item)
        t4 = time.time()
        print(f'Update IR data: {t1-t0:.3f}, Update table: {t2-t1:.3f}, Update count: {t3-t2:.3f}, Update data: {t4-t3:.3f}, total: {t4-t0:.3f}')
    
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
