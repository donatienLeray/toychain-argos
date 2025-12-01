from toychain.src.State import StateMixin
from toychain.src.utils.helpers import gen_enode
from loop_functions.params import params as lp
import logging
import warnings

logger = logging.getLogger('sc')

class Contract(StateMixin):

    def __init__(self, state_variables = None):

        if state_variables is not None:
            for var, value in state_variables.items(): setattr(self, var, value)     

        else:
            
            self.n           = 0
            self.private     = {}
            self.balances    = {}
            # Custom state variables
            # required parameters for initialization
            required = [
                ("scs", "update"),
                ("scs", "decay"),
                ("scs", "trans_reward"),
                ("generic", "num_robots"),
            ]
            # check for required parameters are given
            for k,j in required:
                if k not in lp or j not in lp[k]:
                    print(f"\033[93mMissing required parameter lp['{k}']['{j}'] for initializing smart contract state variables.\033[0m")
                
            self.all_hellos  = {}
            self.connectivity = [gen_enode(i+1) for i in range(int(lp['generic']['num_robots']))]
            self.trans_reward = int(lp['scs']['trans_reward'])
            self.decay = int(lp['scs']['decay'])
            self.connectivity_update = lp['scs']['update']


    def Hello(self, neighbor):
        
        self.all_hellos.setdefault(neighbor, [])
        self.all_hellos[neighbor].append((self.msg.sender, self.msg.timestamp))
        

        logger.info(f"Robot {self.msg.sender} greeted {neighbor} !")
        
    def get_block_reward(self,block):
        
        self.update_connectivity(block)
        return len(block.data) * self.trans_reward
    
    def update_connectivity(self,block):
        
        # check if a update method is defined
        if not hasattr(self,self.connectivity_update):
            logger.debug(f"{self}.update_connectivity called with no defined connectivity_update")
            return
        else:
            getattr(self,self.connectivity_update)(block)   
        
    def connectivity_Index(self,block):
        timestamp = block.timestamp
        # for each participant 
        for i in self.all_hellos.keys():
            enode = gen_enode(i)
            valid_hellos = len([e for e in self.all_hellos[i] if e[1] > timestamp - self.decay])
            self.connectivity[enode] = valid_hellos  
    
    def none(self):
        pass
    