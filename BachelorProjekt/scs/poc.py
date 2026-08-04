# Import necessary modules for smart contract implementation
from toychain.src.State import StateMixin
from toychain.src.utils.helpers import gen_enode, enode_to_id
from loop_functions.params import params as lp
import logging
import warnings
import os
argos_name = os.environ.get("ARGOSNAME", "").strip().lower()

# Initialize logger for smart contract operations
logger = logging.getLogger('sc')

class Contract(StateMixin):
    """
    Smart contract class that manages blockchain state and operations.
    Inherits from StateMixin to handle state-related functionality.
    """

    def __init__(self, state_variables = None):
        """
        Initialize the smart contract with state variables.
        
        Args:
            state_variables (dict, optional): Pre-configured state variables to load.
                                             If None, initializes with default values.
        """
        # If state_variables are provided, restore them; otherwise initialize defaults
        if state_variables is not None:
            for var, value in state_variables.items(): setattr(self, var, value)     

        else:
            # Initialize basic ledger variables
            self.n           = 0
            self.private     = {}
            self.balances    = {}
            
            # Define required parameters for initialization
            required = [
                ("scs", "update"),
                ("scs", "decay"),
                ("scs", "trans_reward"),
                ("generic", "num_robots"),
            ]
            
            # Validate that all required parameters are present in configuration
            for k,j in required:
                if k not in lp or j not in lp[k]:
                    print(f"\033[93mMissing required parameter lp['{k}']['{j}'] for initializing smart contract state variables.\033[0m")
                
            # Initialize connectivity tracking and transaction rewards
            self.all_hellos  = {}
            self.all_peers   = {str(i+1): {} for i in range(int(lp['generic']['num_robots'])) }  # Track peer relationships: {robot_id: [(peer_id, timestamp), ...]}
            self.connectivity = {gen_enode(i+1): 0 for i in range(int(lp['generic']['num_robots'])) }
            self.trans_reward = int(lp['scs']['trans_reward'])
            self.decay = int(lp['scs']['decay'])
            self.connectivity_update = lp['scs']['update']
            
            if argos_name == "foraging":
                self.patches     = []
                self.robots      = {}
                self.credits     = {
                                    'explore': dict(), 
                                    'verify':  dict(),
                                    'forage':  dict()
                                    }
        
        logger.info(f"Initialized smart contract with connectivity update method: {self.connectivity_update}, decay: {self.decay}, transaction reward: {self.trans_reward}")
        if self.connectivity_update == 'recursive_peer_index':
            if ('recursion' not in lp['scs'] or int(lp['scs']['recursion']) < 1):
                warnings.warn("Using 'recursive_peer_index' as connectivity update method without a valid 'recursion' parameter may lead to incorrect connectivity calculations. Please set lp['scs']['recursion'] to a positive integer to specify the number of rounds of recursion for connectivity calculation.")
            else:
                logger.info(f"Using 'recursive_peer_index' with {lp['scs']['recursion']} rounds of recursion for connectivity calculation.")

    def Hello(self, neighbor):
        """
        Record a hello message from the sender to a neighbor.
        
        Args:
            neighbor: The neighbor ID that receives the hello message.
        """
        # Initialize hello list for this neighbor if it doesn't exist
        self.all_hellos.setdefault(neighbor, [])
        
        # Record the sender and timestamp of the hello message
        self.all_hellos[neighbor].append((self.msg.sender, self.msg.timestamp))
        
        # Log the communication event
        logger.info(f"Robot {self.msg.sender} greeted {neighbor} !")
    
    def AddPeer(self, peer_id):
        """
        Record that the sender has this robot as a peer.
        Called when the sender's w3.peers list is updated.
        
        Args:
            peer_id: The ID of the peer that the sender is connected to.
        """
        # Get the sender's ID (the robot making this call)
        sender_id = self.msg.sender
        
        # Initialize peer list for this sender if it doesn't exist
        self.all_peers.setdefault(sender_id, {})
        
        # Record the timestamp of this peer connection for the sender
        self.all_peers[sender_id][str(peer_id)] = self.msg.timestamp
        
        # Log the peer connection event
        #logger.info(f"Robot {sender_id} recorded peer {peer_id}")

        
    def get_block_reward(self, block):
        """
        Calculate the reward for processing a block based on transaction count.
        Updates connectivity metrics before computing the reward.
        
        Args:
            block: The block object containing transaction data.
            
        Returns:
            int: Reward amount calculated as (transaction count * trans_reward).
        """
        # Update connectivity status before calculating reward
        self.update_connectivity(block)
        
        # Reward is proportional to the number of transactions in the block
        return len(block.data) * self.trans_reward
    
    def update_connectivity(self, block):
        """
        Update connectivity metrics by calling the configured update method.
        Dynamically invokes the update strategy specified in configuration.
        
        Args:
            block: The block object to use for connectivity update.
        """
        # Check if the configured update method is defined
        if not hasattr(self, self.connectivity_update):
            logger.debug(f"{self}.update_connectivity called with no defined connectivity_update")
            return
        else:
            # Dynamically call the configured update method
            getattr(self, self.connectivity_update)(block)   
    
    def peer_index(self, block):
        """
        Calculate connectivity based on reciprocal peer connections within decay period.
        For each robot, counts how many other robots have it as a peer (within decay window).
        
        Args:
            block: The block object containing the current timestamp.
        """
        # Get the timestamp from the block
        timestamp = block.timestamp
        
        # For each robot
        for robot_id, peers in self.all_peers.items():
            counter = 0
            enode = gen_enode(int(robot_id))
            
            # If the connectivity is negative (marking for waiting due to the N/2 +1 rule) wait one round less.
            if self.connectivity[enode] < 0:
                self.connectivity[enode] += 1
                
            else:
                # For each peer check ...
                for peer_id, ts in peers.items():
                    # ... that the peer connection is within the decay period and not a self-connection
                    if peer_id != robot_id and ts > timestamp - self.decay:
                        # see if connection is reciprocal by checking if this robot is in the peer's list of peers
                        if self.all_peers.get(peer_id, {}).get(robot_id, -self.decay) > timestamp - self.decay:
                            counter += 1

                # update connectivity value with the count of reciprocal connections
                self.connectivity[enode] = counter
                
    def no_update(self, block):
        """
        only update connectivity by decaying existing values, without adding new peer connections.
        
        Args:
            block: The block object containing the current timestamp.
        """
        # Get the timestamp from the block
        timestamp = block.timestamp
        
        # For each robot
        for robot_id, peers in self.all_peers.items():
            enode = gen_enode(int(robot_id))
            
            # If the connectivity is negative (marking for waiting due to the N/2 +1 rule) wait one round less.
            if self.connectivity[enode] < 0:
                self.connectivity[enode] += 1
                
        
    def none(self, block):
        """
        Placeholder method for a no-op update strategy.
        Used when no connectivity update is needed.
        """
        pass

########### only for foraging experiments, not for general use############
    if argos_name == "foraging":
        
        def robot(self):
            return {'task': -1}
        
        def patch(self, x, y, json):
                return {
                    'x': x,
                    'y': y,
                    'json': json,
                    'id': str(self.n),
                    'explorer': None,
                    'verifiers': [],
                    'foragers':  [],
                    'votes': set(),
                    'votes_remove': set(),
                    'all_x': [],
                    'all_y': [],
                    'status': 'verified',
                    'when_remove': 0
                }
            
        def register(self, task = -1):
        
            logger.info(f"Register #{self.msg.sender}")
    
            if self.msg.sender not in self.robots:
                self.robots[self.msg.sender] = self.robot()
                self.credits['explore'][self.msg.sender] = 0
                self.credits['verify'][self.msg.sender]  = 0
                self.credits['forage'][self.msg.sender]  = 0
    
        def propose(self, x, y, json):
        
            if self.msg.sender not in self.robots:
                self.register()
    
            proposal = self.patch(x, y, json)
    
            proposal["explorer"] = self.msg.sender
    
            self.patches.append(proposal)
    
            logger.info(f"New proposal @ {proposal['x']}, {proposal['y']}:")
    
            self.cleanPatches()
    
        def verify(self, x, y, json, remove = False):
        
            if self.msg.sender not in self.robots:
                self.register()
            
            i, _ = self.findByPos(json['x'], json['y'])
    
            if i == 9999:
                logger.info("Proposal not found")
    
            elif self.msg.sender not in self.patches[i]["verifiers"]:
            
                self.patches[i]["verifiers"].append(self.msg.sender)
    
                if remove:
                    logger.info(f"Voted remove @ {json['x']},{json['y']} with ({x},{y})")
                    self.patches[i]["votes_remove"].add(self.msg.sender)
    
                else:
                    logger.info(f"Update patch @ {json['x']},{json['y']} with ({x},{y})")
                    self.patches[i]["json"] = json
                    self.patches[i]["all_x"].append(x)
                    self.patches[i]["all_y"].append(y)
                    self.patches[i]["x"] = round(sum(self.patches[i]["all_x"])/len(self.patches[i]["all_x"]), 2)
                    self.patches[i]["y"] = round(sum(self.patches[i]["all_y"])/len(self.patches[i]["all_y"]), 2)
                    self.patches[i]["votes"].add(self.msg.sender)
    
                
                if len(self.patches[i]["votes"]) >= 5:
                    self.patches[i]["status"] = 'verified'
    
                if len(self.patches[i]["votes_remove"]) >= 5:
                    self.patches[i]["status"] = 'removed'
                    self.patches[i]["when_remove"] = self.block.height+5
    
                self.credits['explore'][self.patches[i]["explorer"]] += 1
                self.credits['verify'][self.msg.sender] += 1
    
            self.cleanPatches()
                    
          
        def forage(self, x ,y, json):
        
            if self.msg.sender not in self.robots:
                self.register()
    
            i, _ = self.findByPos(json['x'], json['y'])
    
            if i < 9999:
                for verifier in self.patches[i]["votes"]:
                    self.credits['verify'][verifier] += 1
                    
                self.credits['forage'][self.msg.sender] += 1
    
            self.cleanPatches()
    
        def cleanPatches(self):
            for i, patch in enumerate(self.patches):
                if patch["status"] == 'removed' and self.block.height >= patch["when_remove"]:
                    del self.patches[i]
                    break
                
        def getPatches(self):
           return self.patches
        
        def findByPos(self, _x, _y):
            for i in range(len(self.patches)):
                if _x ==  self.patches[i]['json']['x'] and _y == self.patches[i]['json']['y']:
                    return i, self.patches[i]
            return 9999, None
    
        def findById(self, _id):
            for i in range(len(self.patches)):
                if _id == self.patches[i]['id']:
                    return i, self.patches[i]
            return 9999, None
    