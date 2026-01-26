# Import necessary modules for smart contract implementation
from toychain.src.State import StateMixin
from toychain.src.utils.helpers import gen_enode
from loop_functions.params import params as lp
import logging
import warnings

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
            self.all_peers   = {}  # Track peer relationships: {robot_id: [(peer_id, timestamp), ...]}
            self.connectivity = {gen_enode(i+1): 0 for i in range(int(lp['generic']['num_robots'])) }
            self.trans_reward = int(lp['scs']['trans_reward'])
            self.decay = int(lp['scs']['decay'])
            self.connectivity_update = lp['scs']['update']


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
        self.all_peers.setdefault(sender_id, [])
        
        # Record the peer connection with timestamp
        self.all_peers[sender_id].append((peer_id, self.msg.timestamp))
        
        # Log the peer connection event
        logger.info(f"Robot {sender_id} recorded peer {peer_id}")

        
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
        
    def hello_index(self, block):
        """
        Update connectivity based on hello messages received within decay period.
        Only counts hello messages that occurred within the configured decay window.
        
        Args:
            block: The block object containing the current timestamp.
        """
        # Get the timestamp from the block
        timestamp = block.timestamp
        
        # Iterate through all robots that have received hello messages
        for i in self.all_hellos.keys():
            # Generate the enode identifier for this robot
            enode = gen_enode(i)
            
            # Count valid hello messages within the decay period
            valid_hellos = len([e for e in self.all_hellos[i] if e[1] > timestamp - self.decay])
            
            # Update the connectivity value for this robot
            self.connectivity[enode] = valid_hellos  
    
    def peer_index(self, block):
        """
        Calculate connectivity based on reciprocal peer connections within decay period.
        For each robot, counts how many other robots have it as a peer (within decay window).
        
        Args:
            block: The block object containing the current timestamp.
        """
        # Get the timestamp from the block
        timestamp = block.timestamp
        
        # For each robot that has peer records
        for robot_id in self.all_peers.keys():
            # Generate the enode identifier for this robot
            enode = gen_enode(robot_id)
            
            # Count unique peers who have this robot as a peer (within decay period)
            # Check all robots to see if they list this robot_id as a peer
            reciprocal_peers = set()
            
            for other_robot_id, peer_list in self.all_peers.items():
                if other_robot_id != robot_id:
                    # Check if this robot is in the other robot's peer list within decay window
                    for peer_id, peer_timestamp in peer_list:
                        if peer_id == robot_id and peer_timestamp > timestamp - self.decay:
                            reciprocal_peers.add(other_robot_id)
                            break  # Count each peer only once
            
            # Update the connectivity value (count of reciprocal peers)
            self.connectivity[enode] = len(reciprocal_peers)
    
    def none(self):
        """
        Placeholder method for a no-op update strategy.
        Used when no connectivity update is needed.
        """
        pass
    