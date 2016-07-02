from getalllcv import *
##CUSP UO 2016
__author__ = "fbb"

import glob
import numpy as np
import optparse
import sys
import os
import pickle as pkl
import json
import scipy.optimize
import datetime
import itertools
import matplotlib
matplotlib.use('agg')
import pylab as pl
import subprocess
import findsize
from getalllcvPCA import read_to_lc

if __name__=='__main__':
    parser = optparse.OptionParser(usage="getallcv.py 'filepattern' ",
                                   conflict_handler="resolve")
    parser.add_option('--nmax', default=100, type="int",
                      help='number of images to process (i.e. timestamps)')
    parser.add_option('--lmax', default=None, type="int",
                      help='number of lights')
    parser.add_option('--sample_spacing', default=0.25, type="float",
                      help="camera sample spacing (inverse of sample rate)")
    parser.add_option('--coordfile', default=None, type="str",
                      help='coordinates python array (generated by windowFinder.py)')
    parser.add_option('--aperture', default=2, type="int",
                      help="window extraction aperture (1/2 side)")    
    parser.add_option('--stack', default=None, type="str",
                      help='stack python array')
    parser.add_option('--skipfiles', default=150, type="int",
                      help="number of files to skip at the beginning")
     
    options,  args = parser.parse_args()

    print ("options", options)
    print ("args", args, args[0])
    if not len(args) == 1:
        sys.argv.append('--help')
        options,  args = parser.parse_args()         
        sys.exit(0)
        
    filepattern = args[0]
    impath = os.getenv("UIdata") + filepattern
    print ("\n\nUsing image path: %s\n\n"%impath)

    img = glob.glob(impath+"*0000.raw")[0]
    print (img)
    fnameroot = filepattern.split('/')[-1]

    if options.stack:
        print ("(There is a stack", options.stack,")")
        stack = np.load(options.stack)
        imsize  = findsize(stack,
                           filepattern=options.stack.replace('.npy','.txt'))
    else:
        imsize  = findsize(img, filepattern=filepattern)
        stack =np.fromfile(img,dtype=np.uint8).reshape(imsize['nrows'],
                                                                imsize['ncols'],
                                                                imsize['nbands'])

            
    
    print ("Image size: ", imsize)
        
    flist = sorted(glob.glob(impath+"*.raw"))

    print ("Total number of image files: %d"%len(flist))


    nmax = min(options.nmax, len(flist)-options.skipfiles)
    print ("Number of timestamps (files): %d"%(nmax))
    flist = flist[options.skipfiles:nmax+options.skipfiles]    

    if options.coordfile:
        print (options.coordfile)
        try:
            allights = np.load(options.coordfile)
        except:
            print ("you need to create the window mask, you can use windowFinder.py")
            print (options.coordfile)
            sys.exit()
    elif os.path.isfile(filepattern+"_allights.npy"):
        try:
            allights = np.load(filepattern+"_allights.npy")
        except:
            print ("you need to create the window mask, you can use windowFinder.py")
            print (filepattern+"_allights.npy")
            sys.exit()            
    else:
        print ("you need to create the window mask, you can use windowFinder.py")
        print (filepattern+"_allights.npy")
        sys.exit()
        
        
    lmax = len(allights)
    if options.lmax: lmax = min([lmax, options.lmax])
    print ("Max number of windows to use: %d"%lmax)
    outdir0 = '/'.join(filepattern.split('/')[:-1])+'/N%04dS%04d'%(nmax,  options.skipfiles)
    outdir = '/'.join(filepattern.split('/')[:-1])+'/N%04dW%04dS%04d'%(nmax,
                                                                 lmax,
                                                                 options.skipfiles)
    if not os.path.isdir(outdir):
        subprocess.Popen('mkdir -p %s '%outdir, shell=True)
        #os.system('mkdir -p %s '%outdir)
    if not os.path.isdir(outdir0):
        subprocess.Popen('mkdir -p %s/%s'%(outdir0+'pickles'), shell=True)
        #os.system('mkdir -p %s'%outdir0+"/pickles")
        subprocess.Popen('mkdir -p %s/%s'%(outdir0+'gifs'), shell=True)
        #os.system('mkdir -p %s'%outdir0+"/gifs")
    print ("Output directories: ",
           '/'.join(filepattern.split('/')[:-1]), outdir0, outdir)

    
    snr = np.zeros((lmax,6)) * np.nan

    xfreq = np.fft.rfftfreq(nmax, d=options.sample_spacing)    

    for i,cc in enumerate(allights[:lmax]):
            print ("\r### Extracting window {0:d} of {1:d}".format(i+1, lmax))
            sys.stdout.flush()

            x2 = 0 if i%2 == 0 else 2

            afft, a = read_to_lc(int(cc[0]+0.5)-options.aperture,
                                 int(cc[1]+0.5)-options.aperture, 
                                 int(cc[0]+0.5)+options.aperture+1,
                                 int(cc[1]+0.5)+options.aperture+1,
                                 flist, 
                                 filepattern+'_x%d_y%d_ap%d'%(int(cc[0]+0.5),
                                                              int(cc[1]+0.5), 
                                                              options.aperture),
                                 imsize, fft=True, showme=False,
                                 c='w', verbose=False, outdir=outdir0)

            ymax = np.nanmax(afft[2:-5])
            xmaxind = np.where(afft[2:-5] == ymax)[0]
            if np.isnan(ymax):
                ymax, xmax = np.nan, np.nan
            else:
                xmax = xfreq[xmaxind+2]
            #print (a.mean(), a.std(), ymax, xmax)
            snr[i] = np.array([int(cc[0]+0.5), int(cc[1]+0.5),
                               a.mean(), a.std(), ymax, xmax])
    
    
            
    snrt = snr.T
    bin_limits = np.arange(min(x)-0.05, max(x)+0.05, 0.05)  
    points_by_bin = [ [] for _ in bin_limits ]
    for (bin_num, y_value) in zip(searchsorted(bin_limits, snrt[5], "right"), snrt[2]/snrt[3]):
        points_by_bin[bin_num].append(y_value)
    ax = pl.figure().add_subplot(111)
    ax.set_xticklabels(['%.2f'%b for b in bin_limits])
    bp = ax.boxplot(points_by_bin)
