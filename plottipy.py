# -*- coding: utf-8 -*-

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock, DockDrop
import time
import os
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import numpy as np
import serial
from serial.tools import list_ports

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

        self.portSelector = PortSelector(self.ui.portList, self.ui.port_open_b, self.ui.port_close_b, self.ui.port_refresh_b)

        self.curve = self.ui.plot.plot()
        self.data = np.empty(100)
        self.ptr = 0

    def update(self, data):
        self.data[self.ptr] = data
        self.ptr += 1
        if self.ptr >= self.data.shape[0]:
            tmp = self.data
            self.data = np.empty(self.data.shape[0] * 2)
            self.data[:tmp.shape[0]] = tmp
        self.curve.setData(self.data[:self.ptr])
        self.ui.plot.getPlotItem().setLabel('top', "%f" % self.ptr)
        self.curve.setPos(-self.ptr, 0)

class PortSelector():
    def __init__(self,
                 list_w:QtWidgets.QListWidget,
                 open_b:QtWidgets.QPushButton,
                 close_b:QtWidgets.QPushButton,
                 refresh_b:QtWidgets.QPushButton):
        self.list_w = list_w
        self.open_b = open_b
        self.close_b = close_b
        self.refresh_b = refresh_b

        self.ports = []

        self.refresh_b.clicked.connect(self.refresh)

        self.refresh()

    def refresh(self):
        self.ports = [('RND', 'Random generator'),]
        self.ports += list(list_ports.comports())
        self.list_w.clear()
        for port in self.ports:
            self.list_w.addItem(f"{port[0]} - {port[1]}")

    def open(self):
        pass

    def close(self):
        pass



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
    ''' Represents a punching bag; when you punch it, it
        emits a signal that indicates that it was punched. '''
    newData = QtCore.Signal(float)

    def __init__(self, f):
        QtCore.QThread.__init__(self)
        self.newData.connect(f)

    def run(self):
        while 1:
            time.sleep(0.01)
            self.newData.emit(np.random.normal())

gen = Generator(win.update)
gen.start()

win.show()

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys

    for port in list_ports.comports():
        print(port)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
