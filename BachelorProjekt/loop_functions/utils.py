#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import math
import sys, os, psutil
import hashlib
import time
import shutil

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Vector2D
from loop_functions.params import params as lp

for file in lp['files'].values():
    open(file, 'w+').close()


def is_in_circle(point, center, radius):
    dx = abs(point[0] - center[0])
    dy = abs(point[1] - center[1])

    if dx**2 + dy**2 <= radius**2:
        return True 
    else:
        return False

def is_in_rectangle(point, center, width, height = None):
    if not height:
        height = width
    dx = abs(point[0] - center[0])
    dy = abs(point[1] - center[1])

    if dx < width/2 and dy < height/2:
        return True 
    else:
        return False

def getCPUPercent():
    return psutil.cpu_percent()

def getRAMPercent():
    return psutil.virtual_memory().percent

def hash_to_rgb(hash_value):
    # Generate a hash object from the input value
    hash_object = hashlib.sha256(hash_value.encode())

    # Get the first 3 bytes of the hash digest
    hash_bytes = hash_object.digest()[:3]

    # Convert the bytes to an RGB color value
    r = hash_bytes[0]
    g = hash_bytes[1]
    b = hash_bytes[2]

    # Return the RGB color value as a tuple
    return [r, g, b]

def loading_bar(total, current, TPS = None):
    """
    Prints a loading bar
    """ 
    # Get the terminal size
    size = shutil.get_terminal_size()

    # Get the width (number of columns)
    length = size.columns - 45
    # loading bar
    progress = int(current / total * length)
    percentage = int(((current * 100) // total))
    percantage_len=len(str(percentage))
    bar_line = f"[{'#' * progress}{percentage}%{'.' * (length - progress+2-percantage_len)}]"
    # current/total
    buffer_len = len(str(total))- len(str(current))
    eta_line=f" {' ' * buffer_len}{current}/{total}"
    # ETA (if TPS is provided)
    if TPS:
        if not hasattr(loading_bar, 'TPS_count'):
            loading_bar.TPS_count = []
        if not hasattr(loading_bar, 'TPS_time'):
            loading_bar.TPS_time = time.time()
        loading_bar.TPS_count.append(TPS)
        # update the Eta every second
        if time.time() - loading_bar.TPS_time > 0:
            # calculate the average TPS
            TPS = sum(loading_bar.TPS_count) // len(loading_bar.TPS_count)
            remaining = (total - current)
            remaining = remaining // TPS
            # format time
            if remaining >= 3600:
                remaining = f"{remaining//3600}h {remaining//60%60}m"
            elif remaining >= 60:
                remaining = f"{remaining//60}m {remaining%60}s"
            # update the current/total line with ETA
            else: 
                remaining = f"{math.ceil(remaining)}s"
            eta_line = f"{current}/{total} ETA: {remaining} remaining      "
            loading_bar.TPS_time = time.time()
    # print the loading bar, current/total and ETA
    print(f"{bar_line} {eta_line}", end='\r')
    # if only 1 
    if total - current < 2:
        print(f"[{'#' * length}100%] {total}/{total} ETA: 0s remaining")