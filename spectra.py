import numpy as np
import scipy.signal
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def cos_func(x, D, E):
    y = D*np.cos(E*x)
    return y

def compute_error(E):

    #E corresponds to cosine argument guess
    guess = [1, E]
    parameters, covariance = curve_fit(cos_func, dataX, dataY_norm, p0=guess)
    fit_D = parameters[0]
    fit_E = parameters[1]
    fit_cosine = cos_func(dataX, fit_D, fit_E)

    #Calculate sum of squares error
    error = np.sum((dataY_norm - fit_cosine)**2)
    return error

compute_error = np.vectorize(compute_error)

def spectral_curve_fit(data, start, stop):
    #Make data accessible to compute_error function
    global dataX
    global dataY_norm
    dataX=np.array(data.iloc[1:][0])   # Definition of the array for the wavelenghts in nanometers
    dataY=np.array(data.iloc[1:][1])   # Definition of the power in dBm

    #Linearize and normalize data
    dataY_linear = 10 ** (dataY / 10) * 1000
    Max_Trans = np.max(dataY_linear)
    dataY_norm = (dataY_linear / Max_Trans) * 2 - 1

    #Initialize array of guess parameters to iterate over and compute errors
    param_list = np.linspace(start, stop, 100)
    errors = compute_error(param_list)

    #Find parameter corresponding to lowest error
    min_loc = np.where(errors == min(errors))[0][0]
    optimal_params = [1, param_list[min_loc]]

    parameters, covariance = curve_fit(cos_func, dataX, dataY_norm, p0=optimal_params)
    fit_D = parameters[0]  # Fit for the amplitue
    fit_E = parameters[1]  # Fit for the argument of the cosine
    fit_cosine = cos_func(dataX, fit_D, fit_E)
    return dataX, dataY_norm, fit_cosine


def temperature_shift(data1, data2, start, end):
    dataX_1 = np.array(data1.iloc[1:][0])  # Definition of the array for the wavelenghts in nanometers
    dataY_1 = np.array(data1.iloc[1:][1])  # Definition of the power in dBm

    dataX_2 = np.array(data2.iloc[1:][0])  # Definition of the array for the wavelenghts in nanometers
    dataY_2 = np.array(data2.iloc[1:][1])  # Definition of the power in dBm

    # Partition data1 to get just the first minimum
    dataX1_peak1 = dataX_1[(dataX_1 > start) & (dataX_1 < end)]
    dataY1_peak1 = dataY_1[(dataX_1 > start) & (dataX_1 < end)]

    # Find minimum, find wavelength corresponding to power minimum
    power_min = min(dataY1_peak1)
    dataX1_minimum = dataX1_peak1[dataY1_peak1 == power_min]

    # Partition data2 to get just the first minimum
    dataX2_peak1 = dataX_2[(dataX_2 > start) & (dataX_2 < end)]
    dataY2_peak1 = dataY_2[(dataX_2 > start) & (dataX_2 < end)]

    # Find minimum, find wavelength corresponding to power minimum
    power_min = min(dataY2_peak1)
    dataX2_minimum = dataX2_peak1[dataY2_peak1 == power_min]

    # Calculate distance between minima of data to get temperature shift
    shift_distance = dataX2_minimum[0] - dataX1_minimum[0]

    plt.plot(dataX1_peak1, dataY1_peak1, label='Signal 1')
    plt.plot(dataX2_peak1, dataY2_peak1, label='Signal 2')
    plt.hlines(y=power_min, xmin=dataX1_minimum[0], xmax=dataX2_minimum[0], color='black', linestyle='dashed',
               label='Distance Shift')
    plt.annotate(f'Shift distance: {round(abs(shift_distance), 3)} nm', xy=(dataX1_minimum[0], power_min + 1))

    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Transmission (dbm)")
    plt.legend()
    plt.show()

def calculate_FSR(data, peak1_start, peak1_end, peak2_start, peak2_end):

    dataX = np.array(data.iloc[1:][0])  # Definition of the array for the wavelenghts in nanometers
    dataY = np.array(data.iloc[1:][1])  # Definition of the power in dBm
    dataY_linear = 10 ** (dataY / 10) * 1000

    dataX_peak1 = dataX[(dataX > peak1_start) & (dataX < peak1_end)]
    dataY_peak1 = dataY_linear[(dataX > peak1_start) & (dataX < peak1_end)]

    # Calculate the maximum of peak 1
    max_peak1 = np.max(dataY_peak1)

    # Calculate wavelength associated with maximum of peak 1
    max_wavelength1 = dataX_peak1[dataY_peak1 == max_peak1]

    # Slice data based for peak 2
    dataX_peak2 = dataX[(dataX > peak2_start) & (dataX < peak2_end)]
    dataY_peak2 = dataY_linear[(dataX > peak2_start) & (dataX < peak2_end)]

    # Calculate the maximum of peak 2
    max_peak2 = np.max(dataY_peak2)

    # Calculate wavelength associated with maximum of peak 2
    max_wavelength2 = dataX_peak2[dataY_peak2 == max_peak2]

    # Calculate differences between peaks

    FSR = max_wavelength2 - max_wavelength1

    plt.plot(dataX, dataY_linear, label='Long MZI', color='blue')
    plt.hlines(y=max_peak2, xmin=max_wavelength1, xmax=max_wavelength2, color='blue', linestyle='dashed', label='FSR')
    plt.axvline(x=peak1_start, linestyle='dashed', color='black')
    plt.axvline(x=peak1_end, linestyle='dashed', color='black')
    plt.axvline(x=peak2_start, linestyle='dashed', color='black')
    plt.axvline(x=peak2_end, linestyle='dashed', color='black')

    # plt.annotate(f'Shift distance: {round(FSR[0], 3)} nm', xy=(max_wavelength1, max_peak1 + .2))
    plt.text(max_wavelength1, max_peak1 + .5, f'Shift distance: {round(FSR[0], 3)} nm',
             bbox={'facecolor': 'white', 'pad': 4})
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Transmission (uW)")
    plt.show()
