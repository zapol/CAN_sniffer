
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtGui import QColor
from ui_MainWindow import Ui_MainWindow
import queue
import serial
import time
import struct
import numpy as np
import argparse

ROWS = 4
COLS = 16
TOTAL_PIXELS = ROWS * COLS
MIN_COLOR = QColor.fromRgbF(0, 0, 1)  # Blue for the minimum temperature
MAX_COLOR = QColor.fromRgbF(1, 0, 0)  # Red for the maximum temperature

class CAN_Sniffer(QtWidgets.QMainWindow):
    def __init__(self, parent=None, port=None):
        super(CAN_Sniffer, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.serial = None
        self.rcv_buffer = bytearray()
        self.messages = {}
        self.ir_data = np.zeros(TOTAL_PIXELS, dtype=np.int16)

        self.data_q = queue.Queue()
        self.error_q = queue.Queue()
        self.timer = QtCore.QTimer()

        self.timer.timeout.connect(self.read_data)
        self.ui.serialPortSelectPb.clicked.connect(self.on_select_port)

        if port is not None:
            self.connect_to_port(port)

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
                # print(f'CanRxMsg: {CanRxMsg}')
                self.update_data(CanRxMsg)
                self.rcv_buffer = self.rcv_buffer[end_idx:]
            else:
                break

    def update_ir_data(self, std_id, new_data):
        if 0x100 <= std_id <= 0x10F:
            index = (std_id - 0x100) * 4
            self.ir_data[index:index + 4] = new_data

    def update_data(self, CanRxMsg):
        std_id, ext_id, ide, rtr, dlc, data, fmi = CanRxMsg
        new_message = True
        
        self.update_ir_data(std_id, struct.unpack('<4h', data[:8]))
        self.ui.tMinLabel.setText(f'{np.min(self.ir_data)/10:.1f}°C')
        self.ui.tMaxLabel.setText(f'{np.max(self.ir_data)/10:.1f}°C')
        self.ui.tAvgLabel.setText(f'{np.mean(self.ir_data)/10:.1f}°C')
        self.update_ir_image()

        if ide == 0x00000000:
            msg_id = std_id
        elif ide == 0x00000004:
            msg_id = ext_id
        else:
            print(f"Unhandled IDE value: 0x{ide:08X}")
            return

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

        # Update the count
        count_item = self.ui.dataTable.item(row_position, 1)
        new_count = int(count_item.text()) + 1
        count_item.setText(str(new_count))

        # Update the data bytes (B0 to B7)
        data_bytes = CanRxMsg[5]
        for i in range(8):
            new_value = f'{data_bytes[i]:2X}'
            try:
                old_value = self.ui.dataTable.item(row_position, 2 + i).text()
            except AttributeError:
                old_value = None

            item = QtWidgets.QTableWidgetItem(new_value)

            if i >= dlc:
                item.setBackground(QtGui.QColor(200, 200, 200))
            elif new_message or new_value != old_value:
                item.setBackground(QtGui.QColor(255, 255, 0))
            self.ui.dataTable.setItem(row_position, 2 + i, item)

    def update_ir_image(self):
        if not np.all(self.ir_data == 0):
            reshaped_data = self.ir_data.reshape((COLS, ROWS))
            # rotate 90 degrees
            reshaped_data = np.rot90(reshaped_data, 3)
            height, width = reshaped_data.shape
            min_val = np.min(reshaped_data)
            max_val = np.max(reshaped_data)
            rgb_data = np.zeros((height, width, 3), dtype=np.uint8)

            for y in range(height):
                for x in range(width):
                    normalized_temp = (reshaped_data[y, x] - min_val) / (max_val - min_val)
                    color = QColor.fromRgbF(
                        MIN_COLOR.redF() + normalized_temp * (MAX_COLOR.redF() - MIN_COLOR.redF()),
                        MIN_COLOR.greenF() + normalized_temp * (MAX_COLOR.greenF() - MIN_COLOR.greenF()),
                        MIN_COLOR.blueF() + normalized_temp * (MAX_COLOR.blueF() - MIN_COLOR.blueF())
                    )
                    rgb_data[y, x, 0] = color.red()
                    rgb_data[y, x, 1] = color.green()
                    rgb_data[y, x, 2] = color.blue()

            image = QtGui.QImage(rgb_data.data, width, height, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(image)
            self.ui.irImage.setScene(QtWidgets.QGraphicsScene())
            self.ui.irImage.scene().addPixmap(pixmap)
            self.ui.irImage.fitInView(self.ui.irImage.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def read_errors(self):
        errors = False
        while not self.error_q.empty():
            error_msg = self.error_q.get()
            self.ui.statusbar.showMessage(error_msg)
            print(error_msg)
            errors = True
        return errors
    
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
