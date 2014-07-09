from PyQt4 import QtCore, QtGui

from ui_MainWin import Ui_MainWindow
from eblib.serialutils import full_port_name, enumerate_serial_ports
import Queue
from com_monitor import ComMonitorThread
from eblib.utils import get_all_from_queue, get_item_from_queue


class CAN_Sniffer(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(CAN_Sniffer, self).__init__(parent)

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)

        self.monitor_active = False
        self.com_monitor = None
        self.com_data_q = None
        self.com_error_q = None
        self.data = ""
        # self.livefeed = LiveDataFeed()
        # self.temperature_samples = []
        self.timer = QtCore.QTimer()

        self.ui.serialPortSelectPb.clicked.connect(self.on_select_port)
        self.ui.serialConnectPb.clicked.connect(self.on_start)
        self.ui.serialDisconnectPb.clicked.connect(self.on_stop)
        self.ui.serialConnectPb.setEnabled(False)
        self.ui.serialDisconnectPb.hide()

    # @QtCore.pyqtSlot(int)
    # def on_inputSpinBox1_valueChanged(self, value):
    #     self.ui.outputWidget.setText(str(value + self.ui.inputSpinBox2.value()))

    # @QtCore.pyqtSlot(int)
    # def on_inputSpinBox2_valueChanged(self, value):
    #     self.ui.outputWidget.setText(str(value + self.ui.inputSpinBox1.value()))

        self.ui.dataTable.setColumnWidth(0,50)
        self.ui.dataTable.setColumnWidth(1,50)
        # for i in range(2,10):
        #     self.ui.dataTable.setColumnWidth(i,25)

        # self.update_data(512, [2,3,4,5,6,7,8,9])
        # self.update_data(654, [1,1,1,1,1,1,1,1])
        # self.update_data(543, [6,8,4,8,2,6,5,8])
        # self.update_data(456, [4,5,7,9,23,7,9,3])
        # self.update_data(512, [5,8,2,78,9,2,78,8])
        # self.update_data(512, [3,78,9,23,78,8,3])
        # self.update_data(512, [3,78,10,23,78])

    def on_select_port(self):
        ports = list(enumerate_serial_ports())
        if len(ports) == 0:
            QMessageBox.critical(self, 'No ports',
                'No serial ports found')
            return
        
        item, ok = QtGui.QInputDialog.getItem(self, 'Select a port',
                    'Serial port:', ports, 0, False)
        
        if ok and not item.isEmpty():
            self.ui.serialConnectPb.setEnabled(True)
            self.ui.serialPortLbl.setText(item)            
            # self.set_actions_enable_state()

    def on_stop(self):
        """ Stop the monitor
        """
        if self.com_monitor is not None:
            self.com_monitor.join(0.01)
            self.com_monitor = None

        self.monitor_active = False
        self.timer.stop()
        # self.set_actions_enable_state()
        
        self.ui.statusbar.showMessage('Monitor idle')
        self.ui.serialConnectPb.show()
        self.ui.serialDisconnectPb.hide()

    
    def on_start(self):
        """ Start the monitor: com_monitor thread and the update
            timer
        """
        if self.com_monitor is not None or self.ui.serialPortLbl.text() == '':
            return
        
        self.data_q = Queue.Queue()
        self.error_q = Queue.Queue()
        self.com_monitor = ComMonitorThread(
            self.data_q,
            self.error_q,
            full_port_name(str(self.ui.serialPortLbl.text())),
            38400)
        self.com_monitor.start()
        
        com_error = get_item_from_queue(self.error_q)
        if com_error is not None:
            QMessageBox.critical(self, 'ComMonitorThread error',
                com_error)
            self.com_monitor = None

        self.monitor_active = True
        # self.set_actions_enable_state()
        
        # self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_timer)
        # self.connect(self.timer, SIGNAL('timeout()'), self.on_timer)
        
        update_freq = 100
        if update_freq > 0:
            self.timer.start(1000.0 / update_freq)
        
        self.ui.statusbar.showMessage('Monitor running')
        self.ui.serialConnectPb.hide()
        self.ui.serialDisconnectPb.show()

    
    def on_timer(self):
        """ Executed periodically when the monitor update timer
            is fired.
        """
        self.read_serial_data()
        # self.update_monitor()

    def read_serial_data(self):
        """ Called periodically by the update timer to read data
            from the serial port.
        """
        qdata = list(get_all_from_queue(self.data_q))
        if len(qdata) > 0:
            data = self.data+''.join(qdata)
            while data.find("Id: ")!=-1:
                msgStart = data.find("Id: ")
                msgEnd = data.find("\n",msgStart)
                if msgEnd == -1:
                    break

                packet = data[msgStart:msgEnd-1]
                # print "msg: [%s]" % packet
                msgId = int(packet[4:8],16)
                # print "msgId: %d [%x]" % (msgId, msgId)
                msgData = map(lambda x: int(x,16) ,packet[16:].split(" "))
                # print "data: ", msgData
                self.update_data(msgId, msgData)

                data = data[msgEnd:]
            self.data = data

    def update_data(self, msgId, msgData):
        rowCount = self.ui.dataTable.rowCount()
        print rowCount
        msgIdExists = False
        for i in range(rowCount):
            if self.ui.dataTable.item(i, 0).text() == "%04X" % msgId:
                msgIdExists = True
                count = int(self.ui.dataTable.item(i, 1).text())
                self.ui.dataTable.item(i, 1).setText(str(count+1))
                for j in range(8):
                    try:
                        txt = "%02X" % msgData[j]
                    except IndexError:
                        txt = ""
                    if self.ui.dataTable.item(i, 2+j).text() != txt:
                        self.ui.dataTable.item(i, 2+j).setText(txt)
                        self.ui.dataTable.item(i, 2+j).setBackground(QtGui.QColor('red'))
                    else:
                        self.ui.dataTable.item(i, 2+j).setBackground(QtGui.QColor('white'))



        if not msgIdExists:
            self.ui.dataTable.insertRow(rowCount)
            print "msgId: %d [%x]" % (msgId, msgId)
            item = QtGui.QTableWidgetItem("%04X" % msgId)
            self.ui.dataTable.setItem(rowCount,0,item)
            item = QtGui.QTableWidgetItem("1")
            self.ui.dataTable.setItem(rowCount,1,item)
            for i in range(8):
                try:
                    item = QtGui.QTableWidgetItem("%02X" % msgData[i])
                except IndexError:
                    item = QtGui.QTableWidgetItem("")
                self.ui.dataTable.setItem(rowCount,2+i,item)

if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    sniffer = CAN_Sniffer()
    sniffer.show()
    sys.exit(app.exec_())
