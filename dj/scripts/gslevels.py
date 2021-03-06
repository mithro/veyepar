#!/usr/bin/python

# gslevel.py
# report audio levels
# to figure out what files are messed up

import optparse
import numpy

import pygtk
pygtk.require ("2.0")
import gobject
gobject.threads_init()
import pygst
pygst.require ("0.10")
import gst

import gtk


class Main:

    def __init__(self, file_name, start_sec, samples):
        
        self.min,self.max = None,None
        self.totals = numpy.array([[0,0],[0,0],[0,0]])
        self.count = 0
        self.samples = samples

        pipeline = gst.Pipeline("mypipeline")
        self.pipeline=pipeline

# source: file
        filesrc = gst.element_factory_make("filesrc", "audio")
        filesrc.set_property("location", file_name)
        pipeline.add(filesrc)

# decoder
        decode = gst.element_factory_make("decodebin", "decode")
        decode.connect("new-decoded-pad", self.OnDynamicPad)
        pipeline.add(decode)
        filesrc.link(decode)

# convert from this to that?!! (I need a better understanding of this element)
        convert = gst.element_factory_make("audioconvert", "convert")
        pipeline.add(convert)
# store to attribute so OnDynamicPad() can get it
        self.convert = convert

# monitor audio levels
        level = gst.element_factory_make("level", "level")
        level.set_property("message", True)
        pipeline.add(level)
        convert.link(level)
        
# send it to alsa        
        # alsa = gst.element_factory_make("alsasink", "alsa")
        # pipeline.add(alsa)
        # level.link(alsa)
# faster to send to fakesink
        sink = gst.element_factory_make("fakesink", "sink")
        pipeline.add(sink)
        level.link(sink)

# keep refernce to pipleline so it doesn't get destroyed 
        self.pipeline=pipeline

        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        if start_sec:
        # skip first bit (get into the 'normal sounding' part of the talk)
            time_format = gst.Format(gst.FORMAT_TIME)
            seek_ns = (start_sec * 1000000000)
            pipeline.seek_simple(time_format, gst.SEEK_FLAG_FLUSH, seek_ns)

        pipeline.set_state(gst.STATE_PLAYING)

    def OnDynamicPad(self, dbin, pad, islast):

        if pad.get_caps()[0].get_name().startswith('audio'):
            pad.link(self.convert.get_pad("sink"))

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_ELEMENT \
                and message.structure.get_name()=='level':

            levs = [[int(i) for i in message.structure[type]]
                for type in ("rms","peak","decay")]
            # self.totals = [[self.totals[i][j]+int(levs[i][j]) for j in [0,1]] for i in [0,1,2] ]
            self.totals += levs
            self.count += 1
            if self.count == self.samples:
            	self.quit()

        elif t == gst.MESSAGE_EOS:
            self.quit()

    def quit(self):
            self.pipeline.set_state(gst.STATE_NULL)
            gtk.main_quit()

def cklev(file_name, start_sec=None, samples=None):
    p=Main(file_name,start_sec, samples)
    gtk.main()
    return (p.totals/p.count).tolist()

#         levs = gslevels.cklev(rawpathname, 5*60, 500)

def parse_args():
    parser = optparse.OptionParser()
    options, args = parser.parse_args()
    return options,args

if __name__=='__main__':
    options,args = parse_args()
    file_names= args or ['foo.dv']
    levs = cklev(file_names[0], 5*60, 500)
    print levs
