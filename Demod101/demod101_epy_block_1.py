"""
Embedded Python Block
"""

import numpy as np
from gnuradio import gr
import pmt
import array
import numpy
import scipy.signal

tau = numpy.pi * 2
max_samples = 1000000
debug = True

# determine the clock frequency
# input: magnitude spectrum of clock signal (numpy array)
# output: FFT bin number of clock frequency
def find_clock_frequency(spectrum):
    maxima = scipy.signal.argrelextrema(spectrum, numpy.greater_equal)[0]
    while maxima[0] < 2:
        maxima = maxima[1:]
    if maxima.any():
        threshold = max(spectrum[2:-1])*0.8
        indices_above_threshold = numpy.argwhere(spectrum[maxima] > threshold)
        return maxima[indices_above_threshold[0]]
    else:
        return 0

def midpoint(a):
    """
    @brief takes two sets of values, one set is all values above the mean and the other is all values below the mean.
           then it finds the median of each set and returns the value in between the median of each set.
    """
    mean_a = numpy.mean(a)
    mean_a_greater = numpy.ma.masked_greater(a, mean_a)
    high = numpy.ma.median(mean_a_greater)
    mean_a_less_or_equal = numpy.ma.masked_array(a, ~mean_a_greater.mask)
    low = numpy.ma.median(mean_a_less_or_equal)
    midpoint_result = (high + low) / 2
    return midpoint_result

# whole packet clock recovery                                                                                                                                         
# input: real valued NRZ-like waveform (array, tuple, or list)                                                                                                        
#        must have at least 2 samples per symbol                                                                                                                      
#        must have at least 2 symbol transitions                                                                                                                      
# output: list of symbols                                                                                                                                             
def wpcr(a):                                                                                                                                                          
    if len(a) < 4:                                                                                                                                                    
        return []                                                                                                                                                     
                                                                                                                                                                      
    # input conditioning                                                                                                                                              
    b = (a > midpoint(a)) * 1.0 # convert samples into floats of 0 and 1. 0 if the sample is below the midpoint, 1 if it is above
    d = numpy.diff(b)**2        # find symbol transition points and mark with the value 1
    if len(numpy.argwhere(d > 0)) < 2:
        return []
    f = scipy.fft.fft(d, len(a))    # len(a) larger than len(d), so pad d with zeros and find clock frequency
    p = find_clock_frequency(abs(f))
    if p == 0:
        return []
    cycles_per_sample = (p*1.0)/len(f)
    clock_phase = 0.5 + numpy.angle(f[p])/(tau)
    if clock_phase <= 0.5:
        clock_phase += 1
    symbols = []
    for i in range(len(a)):
        if clock_phase >= 1:
            clock_phase -= 1
            symbols.append(a[i])
        clock_phase += cycles_per_sample
    if debug:
        print("peak frequency index: %d / %d" % (p, len(f)))
        print("samples per symbol: %f" % (1.0/cycles_per_sample))
        print("clock cycles per sample: %f" % (cycles_per_sample))
        print("clock phase in cycles between 1st and 2nd samples: %f" % (clock_phase))
        print("clock phase in cycles at 1st sample: %f" % (clock_phase - cycles_per_sample/2))
        print("symbol count: %d" % (len(symbols)))
    return symbols

# convert soft symbols into bits (assuming binary symbols)
def slice_bits(symbols):
    symbols_average = numpy.average(symbols)
    bits = (symbols >= symbols_average)
    return numpy.array(bits, dtype=numpy.uint8)



class blk(gr.sync_block):
    """Packet Format"""

    def __init__(self):
        gr.sync_block.__init__(self,
            name = "Packet Format GR38",
            in_sig = None,
            out_sig = None)
        self.message_port_register_in(pmt.intern('PDU_in'))
        self.message_port_register_out(pmt.intern('PDU_out0'))
        self.set_msg_handler(pmt.intern('PDU_in'), self.handle_msg)

    def handle_msg(self, msg):
        inMsg = pmt.to_python(msg)
        pld = inMsg[1] ## type-> numpy.ndarray
        mLen = len(pld)
        print(type(pld))
        if (mLen > 0):
            symbols=wpcr(pld)
            bits=slice_bits(symbols)
            print(list(bits))
            ## create PMT u8vector using byte array
            #new_out_bytes_pmt=pmt.cons(pmt.PMT_NIL,pmt.init_u8vector(new_bytes_out_len,(byte_array_new_char_list)))
            self.message_port_pub(pmt.intern('PDU_out0'), msg)
