#!/usr/bin/env python3
# Experimental parameters used in loop and qt_user functions
# Reqs: parameter dictionary is named "params"

import math
import os

# All environment variables
params = dict()
params['environ'] = os.environ

# Generic parameters; include adaptations of environment variables
params['generic'] = dict()
params['generic']['time_limit'] = float(os.environ["TIMELIMIT"]) * 60
params['generic']['arena_size'] = float(os.environ["ARENADIM"])
params['generic']['num_robots'] = int(os.environ["NUMROBOTS"])
params['generic']['seed']       = 358 # None for randomgen
params['generic']['tps'] = eval(os.environ["TPS"])
params['generic']['num_1'] = eval(os.environ["NUM1"])
params['generic']['num_2'] = eval(os.environ["NUM2"])
params['generic']['density'] = eval(os.environ["DENSITY"])
params['generic']['arena_dim'] = eval(os.environ["ARENADIM"])
params['generic']['rab_range'] = eval(os.environ["RABRANGE"])
params['generic']['block_period'] = eval(os.environ["BLOCKPERIOD"])
params['generic']['max_workers'] = eval(os.environ["MAXWORKERS"])
params['generic']['regen_rate'] = eval(os.environ["REGENRATE"])

# Initialize the files which store QT_draw information 
params['files'] = dict()

# parameters of the smart contract
params['scs'] = dict()
params['scs']['trans_reward'] = 1
params['scs']['decay'] = 50
params['scs']['lottery_update'] = 'hello_fixed_last'

# debug parameters
params['debug'] = dict()
params['debug']['main'] = True
params['debug']['loop'] = True
