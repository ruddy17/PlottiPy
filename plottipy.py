# -*- coding: utf-8 -*-
import threading
import pyqtgraph as pg
import time
import sys
import struct
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

        self.plots = []
        self.data = []

    def update(self, sample:tuple):
        while len(self.data) < len(sample):
            self.data.append(np.empty(0))
            self.plots.append(self.ui.plot.plot())

        for (i,s) in enumerate(sample):
            self.data[i] = np.append(self.data[i], s)
            self.plots[i].setData(self.data[i])
            # self.ui.plot.getPlotItem().setLabel('top', "%d" % self.data.shape[0])
            self.plots[i].setPos(-self.data[i].shape[0], 0)

    def closeEvent(self, event):
        for p in self.portSelector.getPortList:
            p.close()
        event.accept()

class Emitter(QtCore.QObject):
    newSample = QtCore.pyqtSignal(tuple)

    def __init__(self):
        QtCore.QObject.__init__(self)

    def connect(self):
        self.newSample.connect(win.update)

    def emit(self, data):
        self.newSample.emit(data)


class Port(QtWidgets.QListWidgetItem):

    def __init__(self, port_data, *args, **kwargs):

        self.serial = None
        self.port = port_data[0]
        self.description = port_data[1]
        self.emitter = None
        self.readThread = None
        self.close_request = None

        QtWidgets.QListWidgetItem.__init__(self, f"{port_data[0]} - {port_data[1]}")

    def open(self, baudrate, parity, bytesize):
        self.serial = Serial(timeout=1)
        self.serial.port = self.port
        self.serial.baudrate = int(baudrate)
        self.serial.parity = parity[0]
        self.serial.bytesize = int(bytesize)
        self.serial.open()
        self.readThread = threading.Thread(target=self.listen)
        self.readThread.start()
        self.emitter = Emitter()
        self.emitter.connect()

    def close(self):
        if(self.serial):
            self.serial.close()

    def isOpen(self):
        return self.serial and self.serial.isOpen()

    def __eq__(self, other):
        return (isinstance(other, Port) and self.port == other.port and self.description == other.description)

    def __hash__(self):
        return hash((self.description, self.port))

    def __repr__(self):
        return self.serial.__repr__()

    def listen(self):
        eol = b'\n'
        eol_len = len(eol)
        line = bytearray()

        while True:
            try:
                c = self.serial.read(1)
                if c:
                    line += c
                    if line[-eol_len:] == eol:
                        print(line)
                        sample = struct.unpack('<' + 'h'*(len(line[:-eol_len])//2), line[:-eol_len])
                        print(sample)
                        self.emitter.emit(sample[-2:])
                        line = bytearray()
            except SerialException:
                return
            except AttributeError:
                return
            except struct.error:
                continue


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
                self.list_w.addItem(p)

        # Remove disappeared ports from list
        for i in range(self.list_w.count()):
            if(self.list_w.item(i) is not None):
                p = self.list_w.item(i)
                if p not in new_ports:
                    p.close()
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
            except ValueError as e:
                print(e)
                port.setBackground(QtGui.QColor(255, 0, 0, 127))

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
    win = MainWindow()
    win.show()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(QtGui.QApplication.instance().exec_())
