#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random
import sys, os
import warnings
from collections import Counter as CCounter
#-----------------------------
mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]
#-----------------------------
# controllers
from controllers.actusensors.movement     import RandomWalk
from controllers.actusensors.erandb       import ERANDB
from controllers.actusensors.rgbleds      import RGBLEDs
from controllers.utils import *
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
    warnings.showwarning(f"No consensus module specified in loop_function params, defaulting to ProofOfAuthority")   
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

# intalise Genesis Block
if ConsensusClass.__name__ == 'ProofOfAuthority' or ConsensusClass.__name__ == 'ProofOfWork':
    GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['generic']['num_robots']))], 0, 0, 0, nonce = 1, state = State())
else:
    GENESIS = Block(0, 0000, [], 0, 0, 0, 0, nonce = 1, state = State())

# /* Logging Levels for Console and File */
#######################################################################
import logging
loglevel = 10
logtofile = False 

# /* Experiment Global Variables */
#######################################################################

clocks['peering'] = Timer(10)
clocks['block']   = Timer(BLOCK_PERIOD)

# /* Experiment State-Machine */
#######################################################################

class States(Enum):
    IDLE   = 1
    TRANSACT = 9
    RANDOM   = 10

####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################

def init():
    global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb, robotID
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

    # /* Initialize Console Logging*/
    #######################################################################
    log_folder = experimentFolder + '/logs/' + robotID + '/'

    # Monitor logs (recorded to file)
    name =  'monitor.log'
    os.makedirs(os.path.dirname(log_folder+name), exist_ok=True) 
    logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s] %(message)s'.format(robotID))
    logging.getLogger('sc').setLevel(20)
    logging.getLogger('w3').setLevel(70)

    # /* Initialize submodules */
    #######################################################################

    # /* Init root logger */
    robot.log = logging.getLogger(); robot.log.setLevel(10)

    # /* Init web3.py */
    robot.log.info('Initialising Python Geth Console...')
    #w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority(genesis = GENESIS))
    w3 = Node(robotID, robotIP, 1233 + int(robotID), ConsensusClass(genesis = GENESIS))
    robot.log.info(f'Consensus Mechanism: {ConsensusClass.__name__}')
    robot.log.info(f'Smart Contract: {State.__name__}')

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, w3.key)

    # # /* Init an instance of the buffer for resources  */
    # robot.log.info('Initialising resource buffer...')
    # rb = ResourceBuffer()

    # /* Init E-RANDB __listening process and transmit function
    robot.log.info('Initialising RandB board...')
    erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])

    # #/* Init Resource-Sensors */
    # robot.log.info('Initialising resource sensor...')
    # rs = ResourceVirtualSensor(robot)
    
    # /* Init Random-Walk, __walking process */
    robot.log.info('Initialising random-walk...')
    rw = RandomWalk(robot, cp['scout_speed'])

    # # /* Init Navigation, __navigate process */
    # robot.log.info('Initialising navigation...')
    # nav = Navigate(robot, cp['recruit_speed'])

    # # /* Init odometry sensor */
    # robot.log.info('Initialising odometry...')
    # odo = OdoCompass(robot)

    # # /* Init GPS sensor */
    # robot.log.info('Initialising gps...')
    # gps = GPS(robot)

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start = States.IDLE)

    # List of submodules --> iterate .start() to start all
    submodules = [erb, w3]

    # /* Initialize logmodules*/
    #######################################################################
    # Experiment data logs (recorded to file)
    # name   = 'resource.csv'
    # header = ['COUNT']
    # logs['resources'] = Logger(log_folder+name, header, rate = 5, ID = me.id)

    txs['hi'] = None

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################


def controlstep():
    global clocks, counters, startFlag, startTime

    ###########################
    ######## ROUTINES #########
    ###########################

    def peering():
        
        changed = False

        # Get the current peers from erb if they have higher difficulty chain
        erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}

        # Add peers on the toychain
        for enode in erb_enodes-set(w3.peers):
            try:
                w3.add_peer(enode)
            except Exception as e:
                raise e
            changed = True
            
        # Remove peers from the toychain
        for enode in set(w3.peers)-erb_enodes:
            try:
                w3.remove_peer(enode)
            except Exception as e:
                raise e
            changed = True
            
        if ConsensusClass.__name__ == "ProofOfConnection" and changed:
            # When peers change, record them in the smart contract
            for peer in w3.peers:
                txdata = {'function': 'AddPeer', 'inputs': [enode_to_id(peer)]}
                tx = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(tx)
            changed = False

        # Turn on LEDs according to geth peer count
        rgb.setLED(rgb.all, rgb.presets.get(len(w3.peers), 3*['red']))

    if not startFlag:
        ##########################
        #### FIRST STEP ##########
        ##########################

        startFlag = True 
        startTime = 0

        robot.log.info('--//-- Starting Experiment --//--')

        for module in submodules:
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
        for module in submodules:
            module.step()

        # Perform clock steps
        for clock in clocks.values():
            clock.time.step()

        # # Perform file logging step
        # if logs['resources'].query():
        #     logs['resources'].log([len(rb)])

        if clocks['peering'].query():
            peering()

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

        #########################################################################################################
        #### State::IDLE
        #########################################################################################################
        if fsm.query(States.IDLE):

            fsm.setState(States.RANDOM, message = "Walking randomely to meet peers")

        #########################################################################################################
        #### State::RANDOM
        #########################################################################################################
        if fsm.query(States.RANDOM):

            rw.step()

            if erb.peers:
                neighbor = random.choice(erb.peers)
                fsm.setState(States.TRANSACT, message = f"Greeting peer {neighbor.id}", pass_along=neighbor)
                
        #########################################################################################################
        #### State::TRANSACT  
        #########################################################################################################

        elif fsm.query(States.TRANSACT):

            rw.step()

            if not txs['hi']:
                neighbor = fsm.pass_along

                txdata = {'function': 'Hello', 'inputs': [neighbor.id]}
                txs['hi'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(txs['hi'])

            if w3.get_transaction_receipt(txs['hi'].id):
                txs['hi'] = None
                fsm.setState(States.RANDOM, message = "Transaction success")

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
    header = ['HEIGHT', 'BLOCK', 'TIMESTAMP', 'TELAPSED', 'RECEPTION', 'SIZE_KB', 'TXS', 'DIFF', 'TDIFF', 'HASH', 'PHASH']
    try:
        logs['block'] = Logger(f"{logdir}/{name}", header, ID = robotID)
    except Exception as e:
        robot.log.exception(f"Failed to open block log for robot {robotID}: {e}")
        logs['block'] = None

    name   = 'sc.csv'
    header = ['N', 'PRIVATE', 'BALANCES'] 
    try:
        logs['sc'] = Logger(f"{logdir}/{name}", header, ID = robotID)
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
                    logs['sc'].log(
                        [block.state.n,                                   # N
                         block.state.private if hasattr(block.state, 'private') else {},  # PRIVATE
                         block.state.balances,                            # BALANCES
                        ])
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

