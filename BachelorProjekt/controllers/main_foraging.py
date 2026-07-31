#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random
import sys, os
from unittest.mock import patch
import warnings
import json
import math
from collections import Counter as CCounter
#-----------------------------
mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]
#-----------------------------
# controllers
from MarketForaging.controllers.actusensors.movement     import RandomWalk, GPS, Navigate, OdoCompass
from MarketForaging.controllers.actusensors.groundsensor import ResourceVirtualSensor, Resource
from MarketForaging.controllers.actusensors.erandb       import ERANDB
from MarketForaging.controllers.actusensors.rgbleds      import RGBLEDs
from MarketForaging.controllers.utils import *
from MarketForaging.controllers.utils import FiniteStateMachine
from controllers.utils import hash_to_int
#-----------------------------
# Parameters
from controllers.params import params as cp
from loop_functions.params import params as lp
#-----------------------------
# helpers
from toychain.src.utils.helpers import gen_enode, enode_to_id
import importlib
#-----------------------------
# toychain consensus mechanism
# import the correct consensus mechanism dynamically
if 'consensus' in lp and 'module' in lp['consensus']:
    module_name = "toychain.src.consensus." + lp['consensus']['module']
    module = importlib.import_module(module_name)
    ConsensusClass = getattr(module, lp['consensus']['class'])
    BLOCK_PERIOD = getattr(module, "BLOCK_PERIOD")
else: # default
    from toychain.src.consensus.ProofOfAuthority import ProofOfAuthority as ConsensusClass, BLOCK_PERIOD 
    warnings.warn(f"No consensus module specified in loop_function params, defaulting to ProofOfAuthority")   
# same as choosisng:
#from toychain.src.consensus.ProofOfConnection import ProofOfConnection , BLOCK_PERIOD
#from toychain.src.consensus.ProofOfAuth import ProofOfAuthority , BLOCK_PERIOD
#from toychain.src.consensus.ProofOfWork import ProofOfWork, BLOCK_PERIOD
#from toychain.src.consensus.ProofOfStake import ProofOfStake, BLOCK_PERIOD
#-----------------------------
# toychain core modules
from toychain.src.Block import Block
from toychain.src.Node import Node
from toychain.src.Transaction import Transaction
#-----------------------------
# toychain State
# import the correct smart contract module dynamically
if 'scs' in lp and 'files' in lp['scs']:
    module_name = "scs." + lp['scs']['files']       
    module = importlib.import_module(module_name)
    State = getattr(module, "Contract") 
else: # default
    from scs.poa_w import Contract as State
#-----------------------------



# /* Global Variables */
#######################################################################
global robot
# Robot ID (set in init)
global robotID
robotID = None

global startFlag
startFlag = False

global txList, tripList, submodules
txList, tripList, submodules = [], [], []

global clocks, counters, logs, txs
clocks, counters, logs, txs = dict(), dict(), dict(), dict()

# /* Experiment Global Variables */
#######################################################################

# Store the position of the market and cache
market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})


# intalise Genesis Block
#######################################################################
if ConsensusClass.__name__ == 'ProofOfAuthority' or ConsensusClass.__name__ == 'ProofOfWork':
    GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['generic']['num_robots']))], 0, 0, 0, nonce = 1, state = State())
else:
    GENESIS = Block(0, 0000, [], 0, 0, 0, 0, nonce = 1, state = State())

# /* Logging Levels for Console and File */
#######################################################################
import logging
loglevel = 10
logtofile = False 

# /* Experiment State-Machine */
#######################################################################

class States(Enum):
    PLAN    = 1
    EVADING = 2
    HOMING  = 3
    EXPLORE = 4
    FORAGE  = 5
    ANTENA  = 6
    VERIFY  = 7
    DROP    = 8
    
    
####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################

def init():
    global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb, robotID, robotSPEED, zoneInside, zoneBounds, txs
    robotID = str(int(robot.variables.get_id()[2:])+1)
    robotIP = '127.0.0.1'
    robot.variables.set_attribute("id", str(robotID))
    robot.variables.set_attribute("circle_color", "gray50")
    robot.variables.set_attribute("block", "0")
    robot.variables.set_attribute("tdiff", "0")
    robot.variables.set_attribute("block_hash", str(hash("genesis")))
    robot.variables.set_attribute("state_hash", str(hash("genesis")))
    robot.variables.set_attribute("mempl_hash", str(hash("genesis")))
    robot.variables.set_attribute("mempl_size", "0")
    # special for foraging
    robot.variables.set_attribute("odo_position",repr(Vector2D()))
    robot.variables.set_attribute("scresources", "[]")
    robot.variables.set_attribute("scresources", "[]")
    robot.variables.set_attribute("foraging", "")
    robot.variables.set_attribute("dropResource", "")
    robot.variables.set_attribute("hasResource", "")
    robot.variables.set_attribute("resourceCount", "0")
    robot.variables.set_attribute("depleted", "")
    robot.variables.set_attribute("state", "")
    robot.variables.set_attribute("forageTimer", "0")
    robot.variables.set_attribute("quantity", "0")
    robot.variables.set_attribute("groupSize", "1")
    robot.variables.set_attribute("w3_peers", "[]")
    robot.variables.set_attribute("verified", "[]")
    robot.variables.set_attribute("pending", "[]")
    robot.variables.set_attribute("allpts", "[]")
    robot.variables.set_attribute("erb_range", str(cp['erbDist'] ))

    # /* Initialize Console Logging*/
    #######################################################################
    log_folder = experimentFolder + '/logs/' + robotID + '/'

    # Monitor logs (recorded to file)
    name =  'monitor.log'
    os.makedirs(os.path.dirname(log_folder+name), exist_ok=True) 
    logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s] %(message)s'.format(robotID))
    logging.getLogger('sc').setLevel(20)
    logging.getLogger('w3').setLevel(70)
    logging.getLogger('fsm').setLevel(10)
    
    robot.log = logging.getLogger(); 
    robot.log.setLevel(10)

    # /* Initialize submodules */
    #######################################################################

    # /* Init web3.py */
    robot.log.info('Initialising Python Geth Console...')
    #w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority(genesis = GENESIS))
    w3 = Node(robotID, robotIP, 1233 + int(robotID), ConsensusClass(genesis = GENESIS),publish=True)
    robot.log.info(f'Consensus Mechanism: {ConsensusClass.__name__}')
    robot.log.info(f'Smart Contract: {State.__name__}')

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, w3.key)
    
    #/* Init Resource-Sensors */
    robot.log.info('Initialising resource sensor...')
    rs = ResourceVirtualSensor(robot)

    # /* Init E-RANDB __listening process and transmit function
    robot.log.info('Initialising RandB board...')
    erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])
    
    # /* Init odometry sensor */
    robot.log.info('Initialising odometry...')
    robot.odo = OdoCompass(robot,variance=cp['error'])
    
    # get speed for this robot from the loop_function params
    agent_speeds = lp['generic'].get('agent_speeds', [])
    try:
        robot_idx = max(0, int(robotID) - 1)
    except Exception:
        robot_idx = 0

    if robot_idx < len(agent_speeds):
        robotSPEED = agent_speeds[robot_idx]
    else:
        robotSPEED = lp['generic']['agent_speed']

    robot.log.info(f'Random-walk speed: {robotSPEED}')
    
    # /* Init Random-Walk, __walking process */
    robot.log.info('Initialising random-walk...')
    rw = RandomWalk(robot, robotSPEED)
    
    # /* Init Navigation, __navigate process */
    robot.log.info('Initialising navigation...')
    nav = Navigate(robot, robotSPEED)

    # /* Init GPS sensor */
    robot.log.info('Initialising gps...')
    gps = GPS(robot)

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start = States.PLAN)

    # List of submodules --> iterate .start() to start all
    submodules = [erb, rs, w3, robot.odo, fsm]

    # /* Initialize clocks*/
    #######################################################################
    
    clocks['peering']  = Timer(30)
    clocks['homing']   = Timer(50)
    clocks['explore']  = Timer(300)
    clocks['verify']   = Timer(0)
    clocks['block']    = Timer(BLOCK_PERIOD)
    
    # /* Initialize logmodules*/
    #######################################################################
    
    #txs['hi'] = None
    txs['update'] = None
    #txs['leave'] = None
    #txs['join']  = None
    #txs['drop'] = None
    #txs['update'] = None

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################


def controlstep():
    global clocks, counters, startFlag, startTime

    ###########################
    ######## ROUTINES #########
    ###########################

    def peering():

        # Get the current peers from erb if they have higher difficulty chain
        erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}
        
        # If using ProofOfConnection, update the smart contract with peer changes
        if ConsensusClass.__name__ == "ProofOfConnection" and lp['scs']['update'] != "none":
            # record Peers in the smart contract
            for peer in erb.peers:
                txdata = {'function': 'AddPeer', 'inputs': [peer.id]}
                tx = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(tx)
        
                
        # Add peers on the toychain
        for enode in erb_enodes-set(w3.peers):
            try:
                w3.add_peer(enode)
                # log all peers
                logger.info(f"Robot {me.id} added peer {enode_to_id(enode)} at {w3.custom_timer.time()}")
            except Exception as e:
                raise e
            
        # Remove peers from the toychain
        for enode in set(w3.peers)-erb_enodes:
            try:
                w3.remove_peer(enode)
            except Exception as e:
                raise e

        # Turn on LEDs according to geth peer count
        rgb.setLED(rgb.all, rgb.presets.get(len(w3.peers), 3*['red']))

    def evading(patch):
    
        # Navigate orthogonaly to the patch-market
        targets = [Vector2D(patch['json']['x'], patch['json']['y']).rotate(20, degrees=True),
                   Vector2D(patch['json']['x'], patch['json']['y']).rotate(-20, degrees=True)]
        target = min(targets, key=nav.get_distance_to)
    
        arrived = False
            
        nav.sensor = 'gps'
        if nav.navigate_with_obstacle_avoidance(target) < 0.05:
            arrived = True
    
        nav.sensor = 'odometry'
    
        return arrived
    
    def homing():
 
        # Navigate to the market
        arrived = True
 
        nav.sensor = 'gps'
 
        if nav.get_distance_to(market._pr) < 0.9*market.radius:           
            nav.avoid(move = True)
             
        elif nav.get_distance_to(market._pr) < market.radius and len(w3.peers) > 1:
            nav.avoid(move = True)
 
        else:
            nav.navigate_with_obstacle_avoidance(market._pr)
            arrived = False
 
        nav.sensor = 'odometry'
 
        return arrived
 
    def dropping(resource):
 
        direction = (Vector2D(resource['x'],resource['y'])-market._pv).rotate(-25, degrees = True).normalize()
        target = direction*(market.radius+cache.radius)/2+market._pv
 
        nav.sensor = 'gps'
 
        # Navigate to drop location
        arrived = True
 
        if nav.get_distance_to(market._p) < market.radius + 0.5* (cache.radius-market.radius):
            nav.avoid(move = True)
        else:
            nav.navigate_with_obstacle_avoidance(target)
            arrived = False
 
        nav.sensor = 'odometry'
 
        return arrived
 
    def sensing(gps = False):
 
        # Sense environment for resources
        res = rs.getNew()
 
        if res:
            if gps:
                return {'x':res.x, 'y':res.y, 'json':json.loads(res._json)}
            return {'x':round(res.x + robot.odo.ex, 2), 'y':round(res.y + robot.odo.ey, 2), 'json':json.loads(res._json)}
 
    
    
    
    if not startFlag:
        ##########################
        #### FIRST STEP ##########
        ##########################

        startFlag = True 
        startTime = 0

        robot.log.info('--//-- Starting Experiment --//--')

        for module in [erb, rs, w3]:
            try:
                module.start()
            except:
                robot.log.critical('Error Starting Module: %s', module)
                sys.exit()

        for log in logs.values():
            log.start()

        for clock in clocks.values():
            clock.reset()

    else:

        ##############################
        ##### STATE-MACHINE STEP #####
        ##############################

        #########################################################################################################
        #### State::EVERY
        #########################################################################################################
        
        # Perform submodules step
        for module in [erb, rs, w3, robot.odo, fsm]:
            module.step()

        # Perform clock steps
        for clock in clocks.values():
            clock.time.step()

        # # Perform file logging step
        # if logs['resources'].query():
        #     logs['resources'].log([len(rb)])

        if clocks['peering'].query():
            peering()
            
        # Updated odometry position
        robot.variables.set_attribute("odo_position",repr(robot.odo.getPosition()))
        
        if robot.variables.get_attribute("at") == "cache":
            robot.odo.setPosition()
        
        # Read patch info from blockchain
        patches    = w3.sc.getPatches()
        verified   = [p for p in patches if p['status'] == 'verified' and me.id not in p["votes_remove"]]
        unverified = [p for p in patches if p['status'] == 'pending']
        
        unverified_by_me = [p for p in unverified if me.id not in p['votes']]
        explored_by_me   = [p for p in unverified if me.id == p['explorer']]

        # Update blockchain state on the robot C++ object
        last_block = w3.get_block('last')
        robot.variables.set_attribute("block", str(last_block.height))
        robot.variables.set_attribute("tdiff", str(last_block.total_difficulty))
        robot.variables.set_attribute("prod_block", w3.get_produced_block())
        robot.variables.set_attribute("block_hash", str(last_block.hash))
        robot.variables.set_attribute("state_hash", str(last_block.state.state_hash))
        robot.variables.set_attribute("mempl_hash", w3.mempool_hash(astype='str'))
        robot.variables.set_attribute("mempl_size", str(len(w3.mempool)))

        erb.setData(hash_to_int(last_block.total_difficulty, 2), indices=[1,2])
        erb.setData(hash_to_int(w3.mempool_hash(astype='int'), 1), indices=[3])
        
        # (Visualization only, can comment out)
        robot.variables.set_attribute("verified", str([(p['x'], p['y'], p['json']) for p in patches if p['status'] == 'verified']))
        robot.variables.set_attribute("pending",  str([(p['x'], p['y'], p['json']) for p in patches if p['status'] == 'pending']))
        robot.variables.set_attribute("allpts",  str([(p['all_x'], p['all_y'], p['json']) for p in patches if p['status'] == 'pending']))

        #########################################################################################################
        #### State::PLAN
        #########################################################################################################
        if fsm.query(States.PLAN):
            
            if fsm.elapsed < 100:
                homing()
            
            else:
                # start an exploration bout
                duration = random.gauss(cp['explore_mu'], cp['explore_sg'])*10
                clocks['explore'].set(duration)
                fsm.setState(States.EXPLORE, message = "Duration: %.2f" % duration)

        #########################################################################################################
        #### State::EVADING
        #########################################################################################################

        elif fsm.query(States.EVADING):

            arrived = evading(fsm.pass_along)

            if arrived:
                fsm.setState(States.HOMING)

        #########################################################################################################
        #### State::HOMING
        #########################################################################################################

        elif fsm.query(States.HOMING):

            arrived = homing()

            if arrived:
                fsm.setState(States.PLAN)

        #########################################################################################################
        #### State::EXPLORE
        #########################################################################################################
        if fsm.query(States.EXPLORE):

            rw.step()

            # Look for resources
            patch_gs = sensing()

            # Found resource: propose on chain and go to forage
            if patch_gs and not txs.get('update'):
                txdata = {'function': 'propose', 'inputs': (patch_gs['x'], patch_gs['y'], patch_gs['json'])}
                txs['update'] = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(txs['update'])
                robot.log.info(f"Discovered {patch_gs['json'].get('quality','?')}")
                fsm.setState(States.FORAGE, message = "Found patch", pass_along=patch_gs)
                txs['update'] = None

            elif clocks['explore'].query():
                fsm.setState(States.HOMING, message = "Finished exploring")
                txs['update'] = None

        #########################################################################################################
        #### State::FORAGE
        #########################################################################################################
        elif fsm.query(States.FORAGE):

            patch_to_forage = fsm.pass_along
            arrived  = False
            found    = False
            finished = False
            depleted = False
            
            # Navigate to resource
            distance = nav.navigate_with_obstacle_avoidance((patch_to_forage['x'], patch_to_forage['y']))
            
            # Sense for resources
            patch_gs = sensing()
            
            if distance < 0.8*patch_to_forage['json']['radius']:
                arrived  = True  
            
            if patch_gs and (patch_gs['json']['x'], patch_gs['json']['y']) == (patch_to_forage['json']['x'], patch_to_forage['json']['y']):
                patch_to_forage = patch_gs
                found = True
            
            if int(robot.variables.get_attribute("quantity")) >= cp['max_Q'] or fsm.elapsed > 800:
                finished = True
            
            if robot.variables.get_attribute("depleted") == "True":
                depleted = True
            
            # Arrived but not found: explore within radius
            if arrived and not found:
                rw.step(local=True, target=(patch_to_forage['x'],patch_to_forage['y']))
                        
            elif finished:
                
                if depleted or not found:
                    robot.variables.set_attribute("depleted", "")
                    robot.log.info(f"Resource is: depleted {depleted}/found {found}")
                    patch_to_forage['json']['quantity'] = 0 
                    # txdata = {'function': 'verify', 'inputs': (0, 0, patch_to_forage['json'], True)}
                    # tx = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                    # w3.send_transaction(tx)

                    robot.variables.set_attribute("foraging", "")
                    fsm.setState(States.DROP, message = f"Collected {robot.variables.get_attribute('quantity')} {patch_to_forage['json']['quality']}", pass_along = patch_to_forage)

            elif found:
                robot.variables.set_attribute("foraging", "True")
                nav.avoid(move = True)
                
        #########################################################################################################
        #### State::ANTENA
        #########################################################################################################
        
        elif fsm.query(States.ANTENA):
        
            patch_to_broadcast = fsm.pass_along
        
            nav.sensor = 'gps'
            distance = nav.navigate_with_obstacle_avoidance((patch_to_broadcast['json']['x'], patch_to_broadcast['json']['y']))
        
            if distance < 0.2*patch_to_broadcast['json']['radius']:
                nav.avoid(move=True)
        
            _, patch = w3.sc.findByPos(patch_to_broadcast['json']['x'], patch_to_broadcast['json']['y'])
        
            if patch and patch['explorers'][0] != me.id:
                nav.sensor = 'odometry'
                fsm.setState(States.EVADING, message = "Another broadcasting", pass_along = patch_to_broadcast)
        
            elif patch and patch['status'] in ['verified', 'removed']:
                nav.sensor = 'odometry'
                fsm.setState(States.EVADING, message = "Finished broadcasting", pass_along = patch_to_broadcast)
        
        
        #########################################################################################################
        #### State::VERIFY
        #########################################################################################################
        
        elif fsm.query(States.VERIFY):
                    
            patch_to_verify = fsm.pass_along
            arrived = False
            found   = False
            listen  = False
        
            # Navigate to resource
            distance = nav.navigate_with_obstacle_avoidance((patch_to_verify['x'], patch_to_verify['y']))
                    
            # Sense for resources
            patch_gs = sensing()
        
            if patch_gs and patch_gs['json']['x'] == patch_to_verify['json']['x'] and patch_to_verify['json']['y'] == patch_to_verify['json']['y']:
                found = True
        
            # Navigate to verify
            if distance < 0.9*patch_to_verify['json']['radius']:
                arrived    = True   
        
            # Arrived but not found: explore nearby
            if arrived and not found:
                rw.step(local=True, target=(patch_to_verify['x'],patch_to_verify['y']))
        
                # # Listen for the explorer
                # for peer in erb.peers:
                #     if peer.id in patch_to_verify['explorers']:
                #         explorer = peer
                #         listen = True
        
                # # Can hear broadcast from explorer: navigate towards
                # if listen:
                #     bearing  = explorer.bearing
                #     distance = explorer.range
                #     target = Vector2D(distance, bearing, polar=True)
                #     nav.navigate_with_obstacle_avoidance(target, local = True)
        
                # Found the patch: transact
                if found:
                        
                    txdata = {'function': 'verify', 'inputs': (patch_gs['x'], patch_gs['y'], patch_gs['json'])}
                    txs['update'] =  Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(txs['update'])
                        
                    robot.log.info(f"Verified {patch_to_verify['json']['quality']}")
        
                    fsm.setState(States.EVADING, message = "Verify success", pass_along = patch_to_verify)
                    
                elif fsm.elapsed > 800:
                    txdata = {'function': 'verify', 'inputs': (0, 0, patch_to_verify['json'], True)}
                    txs['update'] =  Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(txs['update'])
        
                    robot.log.info(f"Rejected {patch_to_verify['json']['quality']}")
                    fsm.setState(States.HOMING, message = "Verify failed")
                        
                        

        #########################################################################################################
        #### State::DROP
        #########################################################################################################
        elif fsm.query(States.DROP):

            patch_to_drop = fsm.pass_along
            
            # Navigate home
            arrived = dropping(patch_to_drop)
            
            if arrived:
            
                # Transact to drop resource
                # if not txs['drop']:
                # robot.log.info(f"Dropping.")
                    # txdata = {'function': 'forage', 'inputs': (patch_to_drop['x'], patch_to_drop['y'], patch_to_drop['json'])}
                    # txs['drop'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                    # w3.send_transaction(txs['drop'])
               
                # # Transition state  
                # else:
                #     if w3.get_transaction_receipt(txs['drop'].id):
                robot.variables.set_attribute("dropResource", "True")
            
            if not robot.variables.get_attribute("hasResource"):
                # txs['drop'] = None
                robot.variables.set_attribute("dropResource", "")   
                fsm.setState(States.FORAGE, message = "Dropped: %s" % patch_to_drop['json']['quality'], pass_along = patch_to_drop)    


#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass

def destroy():
    # Ensure we attempt to stop mining and then always try to write/close logs
    try:
        w3.stop_mining()
    except Exception as e:
        robot.log.exception(f"Failed to stop mining for robot {robotID}: {e}")

    try:
        txs_all = w3.get_all_transactions()
        if len(txs_all) != len(set([tx.id for tx in txs_all])):
            print(f'REPEATED TRANSACTIONS ON CHAIN: #{len(txs_all)-len(set([tx.id for tx in txs_all]))}')
    except Exception as e:
        robot.log.exception(f"Failed to fetch transactions for robot {robotID}: {e}")

    if lp['debug']['main']:
        try:
            for key, value in w3.sc.state.items():
                if key != 'connectivity' and key != 'lottery':
                    print(f"{key}: {value}")  
                    
            if "connectivity" in w3.sc.state:
                for key, value in w3.sc.state['connectivity'].items():
                    print(f"{enode_to_id(key)}: {value}")
                    
            elif "lottery" in w3.sc.state:
                for enode, count in CCounter(w3.sc.state['lottery']).items():
                    print(f"{enode_to_id(enode)}: {count}")
        except Exception as e:
            robot.log.exception(f"Failed to print debug state for robot {robotID}: {e}")

    # Make sure the log directory exists for this robot
    logdir = f"{experimentFolder}/logs/{robotID}"
    try:
        os.makedirs(logdir, exist_ok=True)
    except Exception as e:
        robot.log.exception(f"Failed to create log dir {logdir}: {e}")

    name   = 'block.csv'
    header = ['HEIGHT', 'MINER', 'BLOCK', 'TIMESTAMP', 'TELAPSED', 'RECEPTION', 'SIZE_KB', 'TXS', 'DIFF', 'TDIFF', 'HASH', 'PHASH']
    try:
        logs['block'] = Logger(f"{logdir}/{name}", header, ID = robotID)
    except Exception as e:
        robot.log.exception(f"Failed to open block log for robot {robotID}: {e}")
        logs['block'] = None

    name   = 'sc.csv'
    
    if lp['debug']['sc']:
        # Dynamically generate header from the genesis block's state attributes
        try:
            sc_header = list(GENESIS.state.__dict__.keys())
        except Exception:
            robot.log.warning(f"Failed to generate dynamic header for sc log for robot {robotID}, using fallback header")
            sc_header = ['n', 'private', 'balances']  # fallback
    # default header for PoC
    elif ConsensusClass.__name__ in ("ProofOfConnection","ProofOfStake"):
        sc_header = ['n', 'private', 'balances', 'connectivity'] 
    # default header for PoS and PoA
    else:
        sc_header = ['n', 'private', 'balances']
    
    try:
        logs['sc'] = Logger(f"{logdir}/{name}", sc_header, ID = robotID)
    except Exception as e:
        robot.log.exception(f"Failed to open sc log for robot {robotID}: {e}")
        logs['sc'] = None

    # Log each block over the operation of the swarm
    try:
        for block in w3.chain:
            if logs.get('block'):
                try:
                    logs['block'].log(
                        [block.height,                           # HEIGHT
                         block.miner_id,                         # MINER
                         block.number,                           # BLOCK
                         block.timestamp,                        # TIMESTAMP
                         0 if block.reception == 0 else block.reception - block.timestamp,      # TELAPSED
                         block.reception,                        # RECEPTION
                         sys.getsizeof(block) / 1024,            # SIZE (KB)
                         len(block.data),                        # TXS
                         block.difficulty,                       # DIFF
                         block.total_difficulty,                 # TDIFF
                         block.hash,                             # HASH
                         block.parent_hash,                      # PHASH
                        ])
                except Exception as e:
                    robot.log.exception(f"Failed to write to block log for robot {robotID}: {e}")

            if logs.get('sc'):
                try:
                    # Dynamically get values from state attributes matching the header
                    sc_values = [getattr(block.state, attr, None) for attr in sc_header]
                    logs['sc'].log(sc_values)
                except Exception as e:
                    robot.log.exception(f"Failed to write to sc log for robot {robotID}: {e}")
                    
    except Exception as e:
        robot.log.exception(f"Failed while iterating chain for robot {robotID}: {e}")
    finally:
        # Ensure logs are flushed and closed
        try:
            if logs.get('block'):
                logs['block'].file.flush()
                try:
                    os.fsync(logs['block'].file.fileno())
                except Exception:
                    pass
                logs['block'].close()
        except Exception as e:
            robot.log.exception(f"Failed to close block log for robot {robotID}: {e}")
        try:
            if logs.get('sc'):
                logs['sc'].file.flush()
                try:
                    os.fsync(logs['sc'].file.fileno())
                except Exception:
                    pass
                logs['sc'].close()
        except Exception as e:
            robot.log.exception(f"Failed to close sc log for robot {robotID}: {e}")

    # Print which robot was killed
    try:
        print('Killed robot '+ robotID)
    except Exception:
        print('Killed robot')

#########################################################################################################################
#########################################################################################################################
#########################################################################################################################

