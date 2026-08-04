#!/usr/bin/env python3
import random, math
import os

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

params = dict()
params['scout_speed']    = 18
params['recruit_speed']  = 18
params['buy_duration']   = 30
arena_dim = _env_float("ARENADIM", _computed_arena_dim())
params['explore_mu']     = arena_dim / params['scout_speed'] * 100
params['explore_sg']     = 5


params['gsFreq']     = 20
params['erbtFreq']   = 10
params['erbDist']    = 175

params['error']      = 0
params['max_Q']       = 8
