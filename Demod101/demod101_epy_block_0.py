"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import pmt


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, example_param=1.0):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Embedded Python Block',   # will show up in GRC
            in_sig=[np.complex64],
            out_sig=[np.complex64]
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.example_param = example_param
        self.key = pmt.intern("frame_start")
        self.message = []
        self.message_threshold = 750

    def work(self, input_items, output_items):
        # demod
        bits = [1 if np.real(samp) > 0 else -1 for samp in input_items[0]]
        output_items[0][:] = bits

        self.message = self.message + bits
        if(len(self.message) > self.message_threshold):

            # find start of frame
            start_code = [1, -1] * 14
            threshold = 25 # max achievable threshold is 28 (i.e. length of start code)
            correlation = np.correlate(start_code, self.message)
            indices = np.where(correlation > threshold)[0]
            if(len(indices) >= 1):
                self.add_item_tag(0, self.nitems_written(0) + indices[0], self.key, pmt.intern(str(correlation[indices[0]])))
            print(len(correlation))

            # print out message and reset length
            self.message = []
        
        return len(output_items[0])
