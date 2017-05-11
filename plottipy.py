# -*- coding: utf-8 -*-
import threading
from hashlib import md5
from serial_parser import SerialParser
import pyqtgraph as pg
import time
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import numpy as np
from serial.tools import list_ports
from serial import Serial, SerialException

pg.setConfigOption('background', pg.mkColor('#31363b'))

# Create main window
pg.mkQApp()

# Define main window class from ui template
WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType('plottipy.ui')

class MainWindow(TemplateBaseClass):
    def __init__(self):
        TemplateBaseClass.__init__(self)

        # Create the main window
        self.ui = WindowTemplate()
        self.ui.setupUi(self)

        self.ui.plot.getPlotItem().setLabel('right', '')
        self.ui.plot.getPlotItem().setLabel('top', '')
        self.ui.plot.getPlotItem().setLabel('left', '')
        self.ui.plot.getPlotItem().setLabel('bottom', '')
        self.ui.plot.setDownsampling(mode='peak')
        self.ui.plot.setClipToView(True)
        self.ui.plot.setRange(xRange=[-100, 0])
        self.ui.plot.setLimits(xMax=0)

        self.portSelector = PortSelector(self.ui.portList,
                                         self.ui.baudrate,
                                         self.ui.parity,
                                         self.ui.bytesize)

        self.curve = self.ui.plot.plot()
        self.data = np.empty(0)
        self.ptr = 0

        self.show()

    def update(self, sample):
        self.data = np.append(self.data, sample)
        self.curve.setData(self.data)
        self.ui.plot.getPlotItem().setLabel('top', "%d" % self.data.shape[0])
        self.curve.setPos(-self.data.shape[0], 0)

class Emitter(QtCore.QObject):
    newSample = QtCore.pyqtSignal(float)

    def __init__(self):
        QtCore.QObject.__init__(self)

    def connect(self):
        self.newSample.connect(win.update)

    def emit(self, data):
        self.newSample.emit(data)

class Port(QtWidgets.QListWidgetItem):

    def __init__(self, port_data, *args, **kwargs):

        self.serial = Serial()
        self.serial.port = port_data[0]
        self.description = port_data[1]
        self.emitter = Emitter()

        self.readThread = threading.Thread(target=self.listen)
        QtWidgets.QListWidgetItem.__init__(self, f"{port_data[0]} - {port_data[1]}")

    def open(self, baudrate, parity, bytesize):
        self.serial.baudrate = int(baudrate)
        self.serial.parity = parity[0]
        self.serial.bytesize = int(bytesize)
        self.serial.open()
        self.readThread.start()
        self.emitter.connect()

    def close(self):
        self.serial.close()

    def isOpen(self):
        return self.serial.isOpen()

    def __eq__(self, other):
        return (isinstance(other, Port) and self.serial.port == other.serial.port and self.description == other.description)

    def __hash__(self):
        return hash((self.description, self.serial.port))

    def __repr__(self):
        return self.serial.__repr__()

    def listen(self):
        while self.serial.isOpen():
            try:
                self.line = self.serial.read(1)
                if self.line:
                    print(self.line)
                    self.emitter.emit(np.random.normal())
                    # self.emitter.emit(str(self.line))
            except SerialException:
                self.close()

class PortSelector():
    def __init__(self,
                 list_w:QtWidgets.QListWidget,
                 baudrate_combo:QtWidgets.QComboBox,
                 parity_combo: QtWidgets.QComboBox,
                 bytesize_combo: QtWidgets.QComboBox):
        self.list_w = list_w
        self.baudrate_combo = baudrate_combo
        self.parity_combo = parity_combo
        self.bytesize_combo = bytesize_combo

        self.baudrate_validator = QtGui.QIntValidator()
        self.baudrate_combo.setValidator(self.baudrate_validator)

        # self.ports = set()
        self.port = None

        self.list_w.itemClicked.connect(self.setPort)

        self.check_availability_list = []
        self.check_availability_timer = QtCore.QTimer()
        self.check_availability_timer.timeout.connect(self.check_availability)
        self.check_availability_timer.start(1000)

        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(1000)

        self.refresh()

    def refresh(self):
        l = list(list_ports.comports())
        new_ports = [Port(p) for p in l]
        old_ports = self.getPortList()

        # Add new ports to list
        for p in new_ports:
            if p not in self.getPortList():
                # item = QtWidgets.QListWidgetItem(f"{p.serial.port} - {p.description}", parent=self.list_w)
                self.list_w.addItem(p)
                # item.setData(QtCore.Qt.UserRole, p)

        # Remove disappeared ports from list
        for i in range(self.list_w.count()):
            if(self.list_w.item(i) is not None):
                p = self.list_w.item(i)
                if p not in new_ports:
                    self.list_w.takeItem(i)

    def setPort(self, port:Port):
        if port.isOpen():
            port.close()
            port.setBackground(QtGui.QColor(0, 0, 0, 0))
        else:
            try:
                port.open(self.baudrate_combo.currentText(),
                          self.parity_combo.currentText(),
                          self.bytesize_combo.currentText())
                port.setBackground(QtGui.QColor(0, 255, 0, 127))
            except SerialException as e:
                print(e)
                port.setBackground(QtGui.QColor(255, 0, 0, 127))
                self.check_availability_list.append(port)
        port.setSelected(False)

        print(self.getPortList())

    def check_availability(self):
        for port in self.check_availability_list:
            try:
                port.serial.open()
                port.serial.close()
                port.setBackground(QtGui.QColor(0, 0, 0, 0))
                del self.check_availability_list[self.check_availability_list.index(port)]
            except SerialException as e:
                print(e)
                port.setBackground(QtGui.QColor(255, 0, 0, 127))

    def getPortList(self)->list:
        return [self.list_w.item(i) for i in range(self.list_w.count())]


win = MainWindow()

# vLine = pg.InfiniteLine(angle=90, movable=False)
# hLine = pg.InfiniteLine(angle=0, movable=False)
# p3.addItem(vLine, ignoreBounds=True)
# p3.addItem(hLine, ignoreBounds=True)

# def mouseMoved(evt):
#     pos = p3.lastMousePos
#     if p3.sceneBoundingRect().contains(pos):
#         mousePoint = p3.getPlotItem().vb.mapSceneToView(pos)
#         index = int(mousePoint.x())
#
#         vLine.setPos(mousePoint.x())
#         hLine.setPos(mousePoint.y())
#
# p3.scene().sigMouseHover.connect(mouseMoved)
#
# def update():
#     global data3, ptr3
#     data3[ptr3] = np.random.normal()
#     ptr3 += 1
#     if ptr3 >= data3.shape[0]:
#         tmp = data3
#         data3 = np.empty(data3.shape[0] * 2)
#         data3[:tmp.shape[0]] = tmp
#     curve3.setData(data3[:ptr3])
#     p3.getPlotItem().setLabel('top', "%f" % ptr3)
#     curve3.setPos(-ptr3, 0)
#     # curve4.setData(data3[:ptr3])
#     # curve4.setPos(-ptr3, 0)

class Generator(QtCore.QThread):
    newData = QtCore.Signal(float)

    def __init__(self, f):
        QtCore.QThread.__init__(self)
        self.newData.connect(f)

    def run(self):
        while 1:
            time.sleep(0.01)
            self.newData.emit(np.random.normal())

# gen = Generator(win.update)
# gen.start()

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
