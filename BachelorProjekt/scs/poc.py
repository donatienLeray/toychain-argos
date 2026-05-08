# Import necessary modules for smart contract implementation
from toychain.src.State import StateMixin
from toychain.src.utils.helpers import gen_enode, enode_to_id
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
            self.all_peers   = {str(i+1): {} for i in range(int(lp['generic']['num_robots'])) }  # Track peer relationships: {robot_id: [(peer_id, timestamp), ...]}
            self.connectivity = {gen_enode(i+1): 0 for i in range(int(lp['generic']['num_robots'])) }
            self.trans_reward = int(lp['scs']['trans_reward'])
            self.decay = int(lp['scs']['decay'])
            self.connectivity_update = lp['scs']['update']
        
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
            enode = gen_enode(int(i))
            
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
        
            
    def recursive_peer_index(self, block):
        """
        Calculate connectivity based on recursive peer connections within decay period.
        For each robot, counts how many other robots have it as a peer, and how many peers those peers have (within decay window).
        
        Args:
            block: The block object containing the current timestamp.
        """
        # call peer_index to get the base connectivity counts
        self.peer_index(block)  
        # Get the timestamp from the block
        timestamp = block.timestamp
        # Set the number of rounds of recursion to perform (can be adjusted based on desired depth of connectivity calculation)
        recursion_rounds= int(lp['scs']['recursion']) if 'recursion' in lp['scs'] else 1
        # Perform the recursive connectivity calculation for the specified number of rounds
        for rr in range(recursion_rounds):
            #make a copy of the connectivity dict to reference the base counts while updating
            base_connectivity = self.connectivity.copy()
            # For each robot
            for robot_id, peers in self.all_peers.items():
                counter = 0
                # For each peer check ...
                for peer_id, ts in peers.items():
                    # ... that the peer connection is within the decay period and not a self-connection
                    if peer_id != robot_id and ts > timestamp - self.decay:
                        # see if connection is reciprocal by checking if this robot is in the peer's list of peers
                        if self.all_peers.get(peer_id, {}).get(robot_id, -self.decay) > timestamp - self.decay:
                            # Add the peer's connectivity value to the count divided by the number of rounds of recursion to prevent exponential growth of connectivity values
                            counter += (base_connectivity.get(gen_enode(int(peer_id)), 0) -1) // (rr + 1) #perhaps chage (rr+1) base.connectivity.get(gen_enode(int(peer_id)), 0)
            
                # update connectivity value with the count of reciprocal connections plus the connectivity of those peers
                enode = gen_enode(int(robot_id))
                self.connectivity[enode] = counter

    def none(self, block):
        """
        Placeholder method for a no-op update strategy.
        Used when no connectivity update is needed.
        """
        pass
    