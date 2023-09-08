# -*- coding: utf-8 -*-

################################################################################
# Form generated from reading UI file 'MainWindow.ui'
##
# Created by: Qt User Interface Compiler version 5.15.2
##
# WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from IrImageWidget import IrImageWidget


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")

        MainWindow.setWindowTitle(u"MainWindow")

        self.centralwidget = QWidget(MainWindow)
        self.verticalLayout = QVBoxLayout(self.centralwidget)

        # Horizontal layout for serial port selection
        self.serialPortHLayout = QHBoxLayout()

        self.serialPortLbl = QLabel(u"Port", self.centralwidget)
        self.serialPortHLayout.addWidget(self.serialPortLbl)

        self.serialPortSelectPb = QPushButton(
            u"Select Port", self.centralwidget)
        self.serialPortHLayout.addWidget(self.serialPortSelectPb)

        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.serialPortHLayout.addItem(self.horizontalSpacer)
        # End of serial port selection

        self.verticalLayout.addLayout(self.serialPortHLayout)

        # Horizontal layout for data table and IR images
        self.mainHLayout = QHBoxLayout()

        # Data table
        self.dataTable = QTableWidget(0, 10, self.centralwidget)
        self.dataTable.setMaximumWidth(500)
        self.dataTable.setHorizontalHeaderLabels(
            [u"ID", u"Count", u"B0", u"B1", u"B2", u"B3", u"B4", u"B5", u"B6", u"B7"])
        self.dataTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dataTable.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.dataTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i in range(10):
            self.dataTable.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeToContents)
        # End of data table

        self.mainHLayout.addWidget(self.dataTable)

        # IR image widgets
        self.irImagesLayout = QGridLayout()

        self.irImages = {"FL": IrImageWidget("FL", self.centralwidget),
                         "FR": IrImageWidget("FR", self.centralwidget),
                         "RL": IrImageWidget("RL", self.centralwidget),
                         "RR": IrImageWidget("RR", self.centralwidget)
                         }
        
        for i, name in enumerate(self.irImages):
            self.irImagesLayout.addWidget(self.irImages[name], i // 2, i % 2)

        # Add spacers below images so that they don't get stretched
        self.irImagesLayout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 2, 0)
        self.irImagesLayout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 2, 1)
        
        

        self.mainHLayout.addLayout(self.irImagesLayout)

        self.verticalLayout.addLayout(self.mainHLayout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
