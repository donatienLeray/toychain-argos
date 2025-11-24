from toychain.src.State import StateMixin
from toychain.src.utils.helpers import gen_enode, enode_to_id
import logging

logger = logging.getLogger('sc')

class Contract(StateMixin):

    def __init__(self, state_variables = None):

        if state_variables is not None:
            for var, value in state_variables.items(): setattr(self, var, value)     

        else:
            self.n           = 0
            self.private     = {}
            self.balances    = {}

            # Init your own state variables
            self.all_hellos  = {}
            self.lottery = []
            self.trans_reward = 0

    def Hello(self, neighbor):
        
        self.all_hellos.setdefault(neighbor, [])
        self.all_hellos[neighbor].append((self.msg.sender, self.msg.timestamp))

        logger.info(f"Robot {self.msg.sender} greeted {neighbor} !")
        
    def get_block_reward(self,block):
        
        self.update_lottery(block)
        return len(block.data) * self.trans_reward
    
    def update_lottery(self,block):
        
        allowed_methods = {
            "market_share"
            "market_fixed"
            "hello_shares"
            "hello_fixed"
            "hello_fixed_last"
         }
        
        # check if a update method is defined
        if not hasattr(self,self.lottery_update):
            logger.debug(f"{self}.update_lottery called with no defined lottery_update")
            return
        # if method is allowed call it.
        func = allowed_methods.get(self.lottery_update)
        if func:
            func(block)
        else:
            logger.warning(f"{self}.update_loterry: \"{self.update_lottery}\" not allowed!")
            getattr(self,self.lottery_update)()   
        
        
    
    def none(self):
        pass
    