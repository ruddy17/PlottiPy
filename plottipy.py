# -*- coding: utf-8 -*-

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock, DockDrop
import time
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import numpy as np
import serial
from serial.tools import list_ports

# Create main window
application = QtGui.QApplication([])
mainWindow = QtGui.QMainWindow()
mainWindow.resize(1000,500)
mainWindow.setWindowTitle('Serial plotter')

# Create dock layout area
area = DockArea()
mainWindow.setCentralWidget(area)

# Create docks
display_dock = Dock("Display", size=(1000,400))
display_dock.hideTitleBar()

port_dock = Dock("Port", size=(1000,100))
port_list = QtWidgets.QComboBox()
port_list.addItem("Random generator")
for port in list_ports.comports():
    port_list.addItem(f"{port[0]} - {port[1]}")
port_dock.addWidget(port_list, col=0)

settings_dock = Dock("Settings")     ## give this dock the minimum possible size

# Lay docks in area
area.addDock(display_dock, 'top')
area.addDock(settings_dock, 'bottom')
area.addDock(port_dock, 'above', settings_dock)

# Fill docks
cw = QtGui.QWidget()

l = QtGui.QVBoxLayout()
cw.setLayout(l)

w = pg.QtGui.QPlainTextEdit()

settings_dock.addWidget(w)

p3 = pg.PlotWidget(name='Plot1')  ## giving the plots names allows us to link their axes together
p3.getPlotItem().setLabel('right','')
p3.getPlotItem().setLabel('top','')
p3.getPlotItem().setLabel('left','')
p3.getPlotItem().setLabel('bottom','')
l.addWidget(p3)

display_dock.addWidget(cw)



p3.setDownsampling(mode='peak')
p3.setClipToView(True)

p3.setRange(xRange=[-100,0])
p3.setLimits(xMax=0)
# p3.disableAutoRange()
# p3.setAutoPan(x=True)
curve3 = p3.plot()
# curve4 = p3.plot()

data3 = np.empty(100)
ptr3 = 0

vLine = pg.InfiniteLine(angle=90, movable=False)
hLine = pg.InfiniteLine(angle=0, movable=False)
p3.addItem(vLine, ignoreBounds=True)
p3.addItem(hLine, ignoreBounds=True)

def mouseMoved(evt):
    pos = p3.lastMousePos
    if p3.sceneBoundingRect().contains(pos):
        mousePoint = p3.getPlotItem().vb.mapSceneToView(pos)
        index = int(mousePoint.x())

        vLine.setPos(mousePoint.x())
        hLine.setPos(mousePoint.y())

p3.scene().sigMouseHover.connect(mouseMoved)

def update():
    global data3, ptr3
    data3[ptr3] = np.random.normal()
    ptr3 += 1
    if ptr3 >= data3.shape[0]:
        tmp = data3
        data3 = np.empty(data3.shape[0] * 2)
        data3[:tmp.shape[0]] = tmp
    curve3.setData(data3[:ptr3])
    p3.getPlotItem().setLabel('top', "%f" % ptr3)
    curve3.setPos(-ptr3, 0)
    # curve4.setData(data3[:ptr3])
    # curve4.setPos(-ptr3, 0)

class Gen(QtCore.QThread):
    ''' Represents a punching bag; when you punch it, it
        emits a signal that indicates that it was punched. '''
    punched = QtCore.Signal()

    def __init__(self, f):
        QtCore.QThread.__init__(self)
        self.punched.connect(f)

    def run(self):
        while 1:
            time.sleep(0.01)
            self.punched.emit()


# timer = pg.QtCore.QTimer()
# timer.timeout.connect(update)
# timer.start(5)

gen = Gen(update)
gen.start()

mainWindow.show()

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys

    for port in list_ports.comports():
        print(port)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
