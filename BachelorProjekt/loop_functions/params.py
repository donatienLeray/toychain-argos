#!/usr/bin/env python3
# Experimental parameters used in loop and qt_user functions
# Reqs: parameter dictionary is named "params"

import math
import os
import random

# All environment variables
params = dict()
params['environ'] = os.environ

# Generic parameters; include adaptations of environment variables
params['generic'] = dict()
params['generic']['time_limit'] = float(os.environ["TIMELIMIT"]) * 60
params['generic']['arena_size'] = float(os.environ["ARENADIM"])
params['generic']['num_robots'] = int(os.environ["NUMROBOTS"])
# Seed for deterministic randomness: read from environment variable `SEED` set by the experiment runner.
# If SEED is empty or invalid, fall back to None (random behavior).
seed_env = os.environ.get("SEED", "")
params['generic']['seed'] = int(seed_env) if seed_env != "" else None


params['generic']['tps'] = eval(os.environ["TPS"])
#params['generic']['num_1'] = eval(os.environ["NUM1"])
#params['generic']['num_2'] = eval(os.environ["NUM2"])
params['generic']['density'] = eval(os.environ["DENSITY"])
params['generic']['arena_dim'] = eval(os.environ["ARENADIM"])
params['generic']['rab_range'] = eval(os.environ["RABRANGE"])
params['generic']['block_period'] = eval(os.environ["BLOCKPERIOD"])
#params['generic']['max_workers'] = eval(os.environ["MAXWORKERS"])
#params['generic']['regen_rate'] = eval(os.environ["REGENRATE"])
params['generic']['consensus'] = str(os.environ["CONSENSUS"])
params['generic']['agent_speed'] = eval(os.environ["AGENTSPEED"])
params['generic']['speed_uniform'] = str(os.environ["SPEEDUNIFORM"])


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

# Initialize the files which store QT_draw information 
params['files'] = dict()

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
