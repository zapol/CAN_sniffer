
from PySide2.QtGui import QImage, QPainter, QPixmap, QColor
from PySide2.QtWidgets import QWidget, QGraphicsScene, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsView
from PySide2 import QtCore
import numpy as np

# IR Image widget
MIN_COLOR = QColor.fromRgbF(0, 0, 1)  # Blue for the minimum temperature
MAX_COLOR = QColor.fromRgbF(1, 0, 0)  # Red for the maximum temperature

class IrImageWidget(QWidget):

    def __init__(self, name:str, parent=None):
        super(IrImageWidget, self).__init__(parent)
        self.setName(name)
        self.setShape(0, 0)

        self.setupUi()
        
    def setupUi(self):
        # Initialize UI components
        self.nameLabel = QLabel(self.name)
        # self.imageLabel = QLabel('IMAGE')
        self.image = QGraphicsView(self)
        self.image.setRenderHint(QPainter.Antialiasing)
        # self.image.setAspectMode
        self.tempMinLabel = QLabel('TempMin: ')
        self.tempAvgLabel = QLabel('TempAvg:')
        self.tempMaxLabel = QLabel('TempMax:')

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.nameLabel)
        # layout.addWidget(self.imageLabel)
        layout.addWidget(self.image)

        # Temperature labels
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.tempMinLabel)
        hlayout.addWidget(self.tempAvgLabel)
        hlayout.addWidget(self.tempMaxLabel)

        layout.addLayout(hlayout)
        self.setLayout(layout)

    def setName(self, name):
        self.name = name

    def setShape(self, rows, columns):
        self.rows = rows
        self.columns = columns
        self.data = np.zeros((rows, columns), dtype=np.int16)

    def updateData(self, data):
        if not np.all(data == 0) and data.shape == self.data.shape:
            # reshaped_data = self.ir_data.reshape((self.rows, self.cols))
            # reshaped_data = np.fliplr(reshaped_data)
            self.data = data
            self.min_val = np.min(self.data)
            self.max_val = np.max(self.data)
            self.avg_val = np.mean(self.data)

            self.tempMinLabel.setText(f'TempMin: {self.min_val:.1f}°C')
            self.tempMaxLabel.setText(f'TempMax: {self.max_val:.1f}°C')
            self.tempAvgLabel.setText(f'TempAvg: {self.avg_val:.1f}°C')

            rgb_data = np.zeros((self.rows, self.columns, 3), dtype=np.uint8)

            for y in range(self.rows):
                for x in range(self.columns):
                    normalized_temp = (self.data[y, x] - self.min_val) / (self.max_val - self.min_val)
                    color = QColor.fromRgbF(
                        MIN_COLOR.redF() + normalized_temp * (MAX_COLOR.redF() - MIN_COLOR.redF()),
                        MIN_COLOR.greenF() + normalized_temp * (MAX_COLOR.greenF() - MIN_COLOR.greenF()),
                        MIN_COLOR.blueF() + normalized_temp * (MAX_COLOR.blueF() - MIN_COLOR.blueF())
                    )
                    rgb_data[y, x, 0] = color.red()
                    rgb_data[y, x, 1] = color.green()
                    rgb_data[y, x, 2] = color.blue()

            image = QImage(rgb_data.data, self.columns, self.rows, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            self.image.setScene(QGraphicsScene())
            self.image.scene().addPixmap(pixmap)
            self.image.fitInView(self.image.sceneRect(), QtCore.Qt.KeepAspectRatio)
        
        else:
            print(f'Invalid data shape: {data.shape}, expected: {self.data.shape}')
