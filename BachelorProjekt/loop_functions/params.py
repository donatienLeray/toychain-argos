#!/usr/bin/env python3
# Experimental parameters used in loop and qt_user functions
# Reqs: parameter dictionary is named "params"

import math
import os
import random


def _env_float(name, default=None):
	value = os.environ.get(name, "")
	if value == "":
		return default
	return float(value)


def _computed_arena_dim():
	num_robots = _env_float("NUMROBOTS")
	density = _env_float("DENSITY")
	rab_range = _env_float("RABRANGE")
	if num_robots is None or density is None or rab_range is None:
		raise RuntimeError("ARENADIM is not set and NUMROBOTS/DENSITY/RABRANGE are incomplete")
	base = math.sqrt(num_robots / density)
	return base + math.sqrt(rab_range * base)

# All environment variables
params = dict()
params['environ'] = os.environ

# Generic parameters; include adaptations of environment variables
params['generic'] = dict()
params['generic']['time_limit'] = float(os.environ["TIMELIMIT"]) * 60
params['generic']['arena_size'] = _env_float("ARENADIM", _computed_arena_dim())
params['generic']['num_robots'] = int(os.environ["NUMROBOTS"])
# Seed for deterministic randomness: read from environment variable `SEED` set by the experiment runner.
# If SEED is empty or invalid, fall back to None (random behavior).
seed_env = os.environ.get("SEED", "")
params['generic']['seed'] = int(seed_env) if seed_env != "" else None


params['generic']['tps'] = eval(os.environ["TPS"])
#params['generic']['num_1'] = eval(os.environ["NUM1"])
#params['generic']['num_2'] = eval(os.environ["NUM2"])
params['generic']['density'] = eval(os.environ["DENSITY"])
params['generic']['arena_dim'] = _env_float("ARENADIM", _computed_arena_dim())
params['generic']['rab_range'] = eval(os.environ["RABRANGE"])
params['generic']['block_period'] = eval(os.environ["BLOCKPERIOD"])
#params['generic']['max_workers'] = eval(os.environ["MAXWORKERS"])
#params['generic']['regen_rate'] = eval(os.environ["REGENRATE"])
params['generic']['consensus'] = str(os.environ["CONSENSUS"])
params['generic']['agent_speed'] = eval(os.environ["AGENTSPEED"])
params['generic']['speed_uniform'] = str(os.environ["SPEEDUNIFORM"])
params['generic']['zone_size'] = _env_float("ZONE_SIZE", 0.5)


def _build_agent_speeds(mean_speed, num_robots, speed_uniform=True, seed=None):
	"""Build one speed per robot.

	If speed_uniform is true, every robot gets the same speed.
	Otherwise, create symmetric pairs around the mean so the average stays
	unchanged. With mean 20 and 5 robots, this can produce [17, 23, 15, 25, 20].
	"""
	mean_speed = float(mean_speed)
	num_robots = int(num_robots)
	speed_uniform = str(speed_uniform).lower() == "true"

	if num_robots <= 0:
		return []

	if speed_uniform:
		return [mean_speed] * num_robots

	rng = random.Random(0 if seed is None else int(seed))
	pair_count = num_robots // 2
	max_offset = max(1, int(round(mean_speed * 0.25)))

	speeds = []
	for _ in range(pair_count):
		offset = rng.randint(1, max_offset)
		speeds.extend([mean_speed - offset, mean_speed + offset])

	if num_robots % 2 == 1:
		speeds.append(mean_speed)

	return speeds


params['generic']['agent_speeds'] = _build_agent_speeds(
	params['generic']['agent_speed'],
	params['generic']['num_robots'],
	speed_uniform=params['generic']['speed_uniform'],
	seed=params['generic']['seed'],
)

# consensus parameters
params['consensus'] = dict()
params['consensus']['module'] = str(os.environ["CONSENSUS"])
params['consensus']['class'] = str(os.environ["CONSENSUS"])
params['consensus']['block_period'] = eval(os.environ["BLOCKPERIOD"])

# parameters of the smart contract
params['scs'] = dict()
params['scs']['files'] = str(os.environ["SCNAME"])
params['scs']['trans_reward'] = 1
params['scs']['decay'] = 50
params['scs']['update'] = "no_update"
params['scs']['recursion'] = 1

# debug parameters
params['debug'] = dict()
params['debug']['main'] = False
params['debug']['loop'] = True
params['debug']['sc'] = False

# Parameters for marketplace
params['market'] = dict()
params['market']['x'] = 0
params['market']['y'] = 0
params['market']['r'] = 3.5 * 0.073/2 * (params['generic']['arena_size'])

# Parameters for cache
params['cache'] = dict()
params['cache']['x'] = params['market']['x']
params['cache']['y'] = params['market']['y']
params['cache']['r'] = 0.09 + params['market']['r']

params['patches'] = dict()
params['patches']['qualities'] = {'blue'}

params['patches']['distribution'] = 'uniform' 
# params['patches']['distribution'] = 'patchy'
# params['patches']['hotspots']      = [{'x_mu': 0.25 * params['generic']['arena_size'], 
# 									     'y_mu': 0.25 * params['generic']['arena_size'], 
# 									     'x_sg': 0.15 * params['generic']['arena_size'], 
# 									     'y_sg': 0.15 * params['generic']['arena_size']}]
# params['patches']['distribution'] = 'fixed' 

params['patches']['counts'] = {'blue': int(round(float(os.environ["PATCHES_COUNT"])))}
# params['patches']['x'] = [ 0.25]
# params['patches']['y'] = [ 0.25]

# params['patches']['counts'] = {'red': 0, 'green': 0, 'blue': 25, 'yellow': 0}
# params['patches']['x'] = [ 0.15, 0.30]
# params['patches']['y'] = [ 0.30, 0.15]

params['patches']['respawn']   = True
params['patches']['known']     = False
params['patches']['radius']    = 0.08
params['patches']['qtty_min']  = 10
params['patches']['qtty_max']  = 35
params['patches']['dist_min']  = 0.2* params['generic']['arena_size']/2
params['patches']['dist_max']  = 1.5 * params['generic']['arena_size']/2

params['patches']['qtty_min']  = {'blue': 10}
params['patches']['qtty_max']  = {'blue': 35}

params['patches']['radii']  = {k: params['patches']['radius'] for k in params['patches']['qualities']}
# params['patches']['radii']  = {k: round(math.sqrt(params['patches']['qtty_min'][k])/20,2) for k in params['patches']['qualities']}

# Parameters for resource economy
params['patches']['utility']     = {'blue': 1}
params['patches']['forage_rate'] = {'blue': 1}
params['patches']['regen_rate']  = {'blue': 5000}

params['patches']['dec_returns'] = dict()
params['patches']['dec_returns']['func']   = 'linear'                       # constant, linear or logarithmic decreasing returns
params['patches']['dec_returns']['thresh'] = 10  # qqty of resource before dec returns starts
params['patches']['dec_returns']['slope']  = 0

params['patches']['dec_returns']['func_robot']  = 'linear'                  # seconds each resource is slower than previous
params['patches']['dec_returns']['slope_robot'] = 0
params['patches']['forage_together'] = False

# params['patches']['dec_returns']['func_robot']  = 'exp'                  # seconds each resource is slower than previous
# params['patches']['dec_returns']['slope_robot'] = 3

# params['patches']['area_percent'] = 0.005 * (10/generic_params['num_robots'])
# params['patches']['radius']    = params['generic']['arena_size']  * math.sqrt(resource_params['area_percent']/math.pi) 

# params['patches']['radius']    = params['generic']['arena_size']  * math.sqrt(resource_params['area_percent']/math.pi) 
# params['patches']['abundancy']    = 0.03
# params['patches']['frequency'] = {'red': 0.25, 'green': 0.25 , 'blue': 0.25, 'yellow': 0.25}

# Parameters for the economy
params['economy'] = dict()
params['economy']['consum_rate'] = {'blue': 1}  # number of resources consumed at the market per block
params['economy']['DEMAND_A'] = 1
params['economy']['DEMAND_B'] = 1
params['economy']['efficiency_distribution'] = 'linear' 
params['economy']['efficiency_best'] = 1  # amps/second of best robot
params['economy']['efficiency_step'] = 0  # amps/second increase per robot ID

# Initialize the files which store QT_draw information 
params['files'] = dict()
params['files']['patches'] = 'loop_functions/patches.txt'
