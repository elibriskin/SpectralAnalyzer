import sys
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QMainWindow, QApplication,
    QLabel, QDialog, QToolBar, QStatusBar,
    QPushButton, QDialogButtonBox,
    QFormLayout, QDoubleSpinBox, QMessageBox,
    QCheckBox, QFileDialog, QComboBox, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSize, QStringListModel

from qt_material import apply_stylesheet

from spectra import cos_func, compute_error, spectral_curve_fit, temperature_shift, calculate_FSR

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

data_list = []
data_labels = []

wavelength_min = 1480
wavelength_max = 1515
class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=2, height=4, dpi=0):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Define plot window
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.initialize_canvas = True

        self.setWindowTitle("Spectral Analysis")
        self.setFixedSize(QSize(800, 550))

        #Index signal selection
        self.data_index = 0

        #Window Toolbar

        toolbar = QToolBar("Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        #Import data
        add_data_button = QAction(QIcon("icons/application--plus.png"), "Add Data", self)
        add_data_button.setStatusTip(("Add spectral data"))
        add_data_button.triggered.connect(self.import_data)
        toolbar.addAction(add_data_button)

        #Linearize data
        linearize_data_button = QAction(QIcon("icons/ui-tooltip--arrow.png"), "Linearize", self)
        linearize_data_button.setStatusTip(("Linearize spectral response"))
        linearize_data_button.triggered.connect(self.linearize_data)
        toolbar.addAction(linearize_data_button)

        #Clear the canvas and all data
        clear_canvas_button = QAction(QIcon("icons/eraser.png"), "Clear canvas", self)
        clear_canvas_button.setStatusTip(("Clear canvas"))
        clear_canvas_button.triggered.connect(self.clear_canvas)
        toolbar.addAction(clear_canvas_button)

        self.setStatusBar(QStatusBar(self))

        # Plotting toolbar

        plotting_toolbar = NavigationToolbar(self.canvas, self)
        toolbar.addWidget(plotting_toolbar)

        #Menu

        #Import Data
        file_import = QAction("&Import Data...", self)
        file_import.triggered.connect(self.import_data)

        #Curve Fit
        curve_fit = QAction("&Curve Fit...", self)
        curve_fit.triggered.connect(self.fit_spectral_data)

        #Temperature Shift
        temperature = QAction("&Temperature Shift...", self)
        temperature.triggered.connect(self.calculate_temperature_shift)

        #FSR Calculation
        FSR = QAction("&FSR...", self)
        FSR.triggered.connect(self.calculate_FSR)

        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        file_menu.addSeparator()
        file_menu.addAction(file_import)

        analyze_menu = menu.addMenu("&Analyze")
        analyze_menu.addSeparator()
        analyze_menu.addAction(curve_fit)
        analyze_menu.addAction(temperature)
        analyze_menu.addAction(FSR)

    def import_data(self):
        menu = FileImportMenu()
        if menu.exec():
            if self.initialize_canvas == True:
                self.setCentralWidget(self.canvas)

            self.initialize_canvas = False

            #Read in spectral data - wavelength and transmission arrays
            data = pd.read_csv(str(menu.file_label.text()), sep=',' , skiprows=0, skip_blank_lines=True, header=None)
            dataX = np.array(data.iloc[1:][0])  # Definition of the array for the wavelenghts in nanometers
            dataY = np.array(data.iloc[1:][1])

            #Append data to stored collection of signal data
            data_list.append(data)
            self.data_index += 1
            data_labels.append(f'Spectral Response {self.data_index}')

            #Draw plot
            if menu.overlay.isChecked() == False:
                self.canvas.ax1.cla()
            self.canvas.ax1.plot(dataX, dataY, label=f'Spectral Response {self.data_index}')
            self.canvas.ax1.set_xlabel("Wavelength (nm)")
            self.canvas.ax1.set_ylabel("Transmission (dbm)")
            self.canvas.ax1.legend(loc='lower right')
            self.canvas.draw()

    def fit_spectral_data(self):
        if len(data_list) == 0:
            error_window = ErrorMenu("No data available!")
            error_window.exec()
            return
        menu = CurveFitMenu()
        if menu.exec():

            #Validate proper parameters for wavelength selection
            if menu.end_param.value () <= menu.start_param.value():
                error_window = ErrorMenu("Start value greater than end value!")
                error_window.exec()
                return

            #Select signal from stored data signal collection
            selected_data = menu.curve_input.currentText()
            selected_index = data_labels.index(selected_data)
            data = data_list[selected_index]

            #Fit curve
            dataX, dataY_norm, fitted_curve = spectral_curve_fit(data, menu.start_param.value(), menu.end_param.value())
            plt.plot(dataX, dataY_norm, label='data')
            plt.plot(dataX, fitted_curve, '-', label='fit')
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Normalized transmission")
            plt.show()

    def calculate_temperature_shift(self):
        if len(data_list) < 2:
            error_window = ErrorMenu("Must have at least two spectral response signals!")
            error_window.exec()
            return
        menu = TemperatureShiftMenu()
        if menu.exec():

            #Parameter validation
            if menu.signal1_input.currentText() == menu.signal2_input.currentText():
                error_window = ErrorMenu("Must select two different signals!")
                error_window.exec()
                return
            if ((menu.start1_param.value() > menu.end1_param.value())):
                error_window = ErrorMenu("Parameters out of bounds!")
                error_window.exec()
                return

            #Select spectral responses for comparison
            selected_data1 = menu.signal1_input.currentText()
            selected_index1 = data_labels.index(selected_data1)
            data1 = data_list[selected_index1]
            selected_data2 = menu.signal2_input.currentText()
            selected_index2 = data_labels.index(selected_data2)
            data2 = data_list[selected_index2]
            temperature_shift(data1, data2, menu.start1_param.value(), menu.end1_param.value())

    def calculate_FSR(self):
        if len(data_list) == 0:
            error_window = ErrorMenu("No data available!")
            error_window.exec()
            return
        menu = FSRMenu()
        if menu.exec():

            #Parameter validation
            if ((menu.peak1_start.value() >= menu.peak1_end.value()) | (menu.peak2_start.value() >= menu.peak2_end.value()) | (menu.peak1_end.value() >= menu.peak2_end.value())):
                error_window = ErrorMenu("Parameters out of bounds!")
                error_window.exec()
                return

            #Select spectral signal to compute FSR
            selected_data = menu.signal_input.currentText()
            selected_index = data_labels.index(selected_data)
            data = data_list[selected_index]
            calculate_FSR(data, menu.peak1_start.value(), menu.peak1_end.value(), menu.peak2_start.value(), menu.peak2_end.value())
    def clear_canvas(self):
        data_list.clear()
        data_labels.clear()
        self.data_index = 0
        self.canvas.ax1.cla()
        self.canvas.draw()

    def linearize_data(self):
        n=0
        self.canvas.ax1.cla()
        if len(data_list) > 0:
            for data in data_list:
                n+=1
                dataX = np.array(data.iloc[1:][0])
                dataY = np.array(data.iloc[1:][1])
                dataY_linear = 10**(dataY/10)*1000
                self.canvas.ax1.plot(dataX, dataY_linear, label=f'Spectral Response {n}')
                self.canvas.ax1.set_xlabel("Wavelength (nm)")
                self.canvas.ax1.set_ylabel("Transmission (uW)")
                self.canvas.ax1.legend(loc='lower right')
                self.canvas.draw()

class FileImportMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Import Spectral Data")

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.file_input = QPushButton(text="Select File...")
        self.file_input.clicked.connect(self.get_files)

        self.file_label = QLabel("")

        self.overlay = QCheckBox("Overlay new data")

        self.layout = QFormLayout()
        self.layout.addWidget(self.file_input)
        self.layout.addWidget(self.file_label)
        self.layout.addWidget(self.overlay)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def get_files(self):
        dlg = QFileDialog()
        filenames = QStringListModel()

        if dlg.exec():
            filenames = dlg.selectedFiles()
            self.file_label.setText(filenames[0])

class CurveFitMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Fit Spectral Data")

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        #Initialize spectral response input
        self.curve_input = QComboBox()
        self.curve_input.addItems(data_labels)

        #Initialize parameter guess value range
        self.start_param = QDoubleSpinBox(minimum=0, maximum=20)
        self.end_param = QDoubleSpinBox(minimum=0, maximum=20)


        self.layout = QFormLayout()
        self.layout.addRow("Spectral response", self.curve_input)
        self.layout.addRow("Starting parameter value", self.start_param)
        self.layout.addRow("Starting ending value", self.end_param)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

class TemperatureShiftMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Calculate Temperature Shift")
        # Define plot window
        self.canvas_temp = MplCanvas(self, width=5, height=4, dpi=100)
        self.initialize_canvas = True

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        #Initiliaze two spectral response inputs
        self.signal1_input = QComboBox()
        self.signal1_input.addItems(data_labels)
        self.signal1_input.activated.connect(self.update_plot)
        self.signal2_input = QComboBox()
        self.signal2_input.addItems(data_labels)

        #Initialize partition point selection
        self.start1_param = QDoubleSpinBox(minimum=wavelength_min, maximum=wavelength_max)
        self.start1_param.valueChanged.connect(self.update_plot)
        self.end1_param = QDoubleSpinBox(minimum=wavelength_min, maximum=wavelength_max)
        self.end1_param.valueChanged.connect(self.update_plot)
        self.layout = QFormLayout()
        self.layout.addRow("Spectral response 1", self.signal1_input)
        self.layout.addRow("Spectral response 2", self.signal2_input)
        self.layout.addRow("Partition Starting Point", self.start1_param)
        self.layout.addRow("Partition Ending Point", self.end1_param)
        self.layout.addWidget(self.canvas_temp)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        selected_data1 = self.signal1_input.currentText()
        selected_index1 = data_labels.index(selected_data1)
        data1 = data_list[selected_index1]
        selected_data2 = self.signal2_input.currentText()
        selected_index2 = data_labels.index(selected_data2)
        data2 = data_list[selected_index2]
        # data1X = np.array(data1.iloc[1:][0])  # Definition of the array for the wavelenghts in nanometers
        # data1Y = np.array(data1.iloc[1:][1])
        # self.canvas_temp.ax1.cla()
        # self.canvas_temp.ax1.plot(data1X, data1Y)
        n=0
        for data in data_list:
            n += 1
            dataX = np.array(data.iloc[1:][0])
            dataY = np.array(data.iloc[1:][1])
            self.canvas_temp.ax1.plot(dataX, dataY, label=f'Spectral Response {n}')
            self.canvas_temp.ax1.set_xlabel("Wavelength (nm)")
            self.canvas_temp.ax1.set_ylabel("Transmission (dbm)")
            self.canvas_temp.ax1.legend(loc='lower right')
        self.line_start = self.canvas_temp.ax1.axvline(self.start1_param.value(), color='black', lw=1, linestyle='--')
        self.line_end = self.canvas_temp.ax1.axvline(self.end1_param.value(), color='black', lw=1, linestyle='--')
        self.canvas_temp.draw()
        # self.canvas.ax1.draw()



    def update_plot(self):
        self.line_start.remove()
        self.line_end.remove()
        self.line_start = self.canvas_temp.ax1.axvline(self.start1_param.value(), color='black', lw=1, linestyle='--')
        self.line_end = self.canvas_temp.ax1.axvline(self.end1_param.value(), color='black', lw=1, linestyle='--')
        self.canvas_temp.draw()
        # selected_data1 = self.signal1_input.currentText()
        # selected_index1 = data_labels.index(selected_data1)
        # data1 = data_list[selected_index1]
        # selected_data2 = self.signal2_input.currentText()
        # selected_index2 = data_labels.index(selected_data2)
        # data2 = data_list[selected_index2]
        # data1X = np.array(data1.iloc[1:][0])  # Definition of the array for the wavelenghts in nanometers
        # data1Y = np.array(data1.iloc[1:][1])
        # self.canvas_temp.ax1.cla()
        # # self.canvas_temp.ax1.plot(data1X, data1Y)
        # self.canvas_temp.ax1.draw()


class FSRMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Calculate FSR")
        self.canvas_FSR = MplCanvas(self, width=5, height=4, dpi=100)
        self.initialize_canvas = True

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        #Initialize signal input
        self.signal_input = QComboBox()
        self.signal_input.addItems(data_labels)
        self.signal_input.activated.connect(self.select_signal)

        #Initialize peak partition points
        self.peak1_start = QDoubleSpinBox(minimum=wavelength_min, maximum=wavelength_max)
        self.peak1_start.valueChanged.connect(self.update_plot)
        self.peak1_end = QDoubleSpinBox(minimum=wavelength_min, maximum=wavelength_max)
        self.peak1_end.valueChanged.connect(self.update_plot)
        self.peak2_start = QDoubleSpinBox(minimum=wavelength_min, maximum=wavelength_max)
        self.peak2_start.valueChanged.connect(self.update_plot)
        self.peak2_end = QDoubleSpinBox(minimum=wavelength_min, maximum=wavelength_max)
        self.peak2_end.valueChanged.connect(self.update_plot)

        self.layout = QFormLayout()
        self.layout.addRow("Spectral response", self.signal_input)
        self.layout.addRow("Peak 1: Partition Starting Point: ", self.peak1_start)
        self.layout.addRow("Peak 1: Partition Ending Point: ", self.peak1_end)
        self.layout.addRow("Peak 2: Partition Starting Point: ", self.peak2_start)
        self.layout.addRow("Peak 2: Partition Ending Point: ", self.peak2_end)
        self.layout.addWidget(self.canvas_FSR)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        data_FSR = data_list[0]
        dataX = np.array(data_FSR.iloc[1:][0])
        dataY = np.array(data_FSR.iloc[1:][1])
        dataY_linear = 10 ** (dataY / 10) * 1000

        self.canvas_FSR.ax1.plot(dataX, dataY_linear, label=f'Spectral Response')
        self.line_peak1_start = self.canvas_FSR.ax1.axvline(self.peak1_start.value(), color='black', lw=1, linestyle='--')
        self.line_peak1_end = self.canvas_FSR.ax1.axvline(self.peak1_end.value(), color='black', lw=1, linestyle='--')
        self.line_peak2_start = self.canvas_FSR.ax1.axvline(self.peak2_start.value(), color='red', lw=1,linestyle='--')
        self.line_peak2_end = self.canvas_FSR.ax1.axvline(self.peak2_end.value(), color='red', lw=1, linestyle='--')

        self.canvas_FSR.ax1.set_xlabel("Wavelength (nm)")
        self.canvas_FSR.ax1.set_ylabel("Transmission (uW)")
        self.canvas_FSR.ax1.legend(loc='lower right')
        self.canvas_FSR.draw()

    def select_signal(self):
        # Select signal from stored data signal collection
        selected_data = self.signal_input.currentText()
        selected_index = data_labels.index(selected_data)
        data_FSR = data_list[selected_index]
        dataX = np.array(data_FSR.iloc[1:][0])
        dataY = np.array(data_FSR.iloc[1:][1])
        dataY_linear = 10 ** (dataY / 10) * 1000
        self.canvas_FSR.ax1.cla()
        self.canvas_FSR.ax1.plot(dataX, dataY_linear, label=f'{selected_data}')
        self.canvas_FSR.ax1.set_xlabel("Wavelength (nm)")
        self.canvas_FSR.ax1.set_ylabel("Transmission (uW)")
        self.canvas_FSR.ax1.legend(loc='lower right')
        self.canvas_FSR.draw()

    def update_plot(self):
        self.line_peak1_start.remove()
        self.line_peak1_end.remove()
        self.line_peak2_start.remove()
        self.line_peak2_end.remove()
        self.line_peak1_start = self.canvas_FSR.ax1.axvline(self.peak1_start.value(), color='black', lw=1,linestyle='--')
        self.line_peak1_end = self.canvas_FSR.ax1.axvline(self.peak1_end.value(), color='black', lw=1, linestyle='--')
        self.line_peak2_start = self.canvas_FSR.ax1.axvline(self.peak2_start.value(), color='red', lw=1,linestyle='--')
        self.line_peak2_end = self.canvas_FSR.ax1.axvline(self.peak2_end.value(), color='red', lw=1, linestyle='--')
        self.canvas_FSR.draw()


class ErrorMenu(QDialog):
    def __init__(self, message):
        super().__init__()

        self.setWindowTitle("ERROR!")

        QBtn = QDialogButtonBox.StandardButton.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        self.message = message
        error_message = QLabel(self.message)
        self.layout.addWidget(error_message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

app = QApplication(sys.argv)

window = MainWindow()

# apply_stylesheet(app, theme='light_teal.xml')
window.show()

app.exec()