
from PySide2.QtGui import QImage, QPainter, QPixmap, QColor
from PySide2.QtWidgets import QWidget, QGraphicsScene
from PySide2 import QtCore
import numpy as np

# IR Image widget
MIN_COLOR = QColor.fromRgbF(0, 0, 1)  # Blue for the minimum temperature
MAX_COLOR = QColor.fromRgbF(1, 0, 0)  # Red for the maximum temperature

class IrImageWidget(QWidget):

    def __init__(self, parent=None):
        super(IrImageWidget, self).__init__(parent)
        self.setShape(0, 0)

        self.ir_image = QImage()
        self.ir_image.convertTo(QImage.Format_RGB888)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.ir_image)

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
            self.ir_image.setScene(QGraphicsScene())
            self.ir_image.scene().addPixmap(pixmap)
            self.ir_image.fitInView(self.ir_image.sceneRect(), QtCore.Qt.KeepAspectRatio)
