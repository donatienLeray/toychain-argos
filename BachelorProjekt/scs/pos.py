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
                ("generic", "num_robots")
            ]
            # check for required parameters are given
            for k,j in required:
                if k not in lp or j not in lp[k]:
                    print(f"\033[93mMissing required parameter lp['{k}']['{j}'] for initializing smart contract state variables.\033[0m")
                
            self.all_hellos  = {}
            self.lottery = [gen_enode(i+1) for i in range(int(lp['generic']['num_robots']))]
            self.trans_reward = int(lp['scs']['trans_reward'])
            self.decay = int(lp['scs']['decay'])
            self.update = lp['scs']['update']

    def Hello(self, neighbor):
        
        self.all_hellos.setdefault(neighbor, [])
        self.all_hellos[neighbor].append((self.msg.sender, self.msg.timestamp))

        logger.info(f"Robot {self.msg.sender} greeted {neighbor} !")
        
    def get_block_reward(self,block):
        
        self.update_lottery(block)
        return len(block.data) * self.trans_reward
    
    def update_lottery(self,block):
        
        allowed_methods = {
            "market_share":self.market_share,
            "market_fixed":self.market_fixed,
            "hello_shares":self.hello_shares,
            "hello_fixed":self.hello_fixed,
            "hello_fixed_last":self.hello_fixed_last
         }
        
        if not hasattr(self,self.update):
            logger.debug(f"{self}.update called with no defined update")
            return
        # if method is allowed call it.
        func = allowed_methods.get(self.update)
        if func:
            func(block)
        else:
            logger.warning(f"{self}.update: \"{self.update}\" not allowed!")
            getattr(self,self.update)()   

    
    # Note: ends up in Monopoly       
    def market_share(self):
        
        market_value = sum(self.balances.values())
        participants = len(self.balances)
        market_share = market_value / participants
        # if the market share is less than the reward for a transaction
        if market_share < self.trans_reward:
            return
        # for each participant 
        for i in self.balances.keys():
            enode = gen_enode(int(i))
            tickets_allowed = self.balances[i] // market_share
            tickets_owned= self.lottery.count(enode)
            # increase or decrease there tickets proportional to theire owned market share
            # make sure they never have less than one ticket
            while tickets_owned < tickets_allowed:
                self.lottery.append(enode)
                tickets_owned += 1
            while tickets_owned > tickets_allowed and tickets_owned > 1:
                self.lottery.remove(enode)
                tickets_owned -= 1
    
    # Note: ends up in Monopoly       
    def market_fixed(self):
        
         for i in self.balances.keys():
            enode = gen_enode(int(i))
            tickets_allowed = self.balances[i] // 10
            tickets_owned= self.lottery.count(enode)
            # increase or decrease there tickets proportional to theire owned market share
            # make sure they never have less than one ticket
            if tickets_owned + 1 <= tickets_allowed:
                self.lottery.append(enode)
                tickets_owned += 1
            while tickets_owned > tickets_allowed and tickets_owned > 1:
                self.lottery.remove(enode)
                tickets_owned -= 1    
                
    def hello_shares(self):
        market_value = sum(len(i) for i in self.all_hellos.values())
        participants = len(self.all_hellos)
        market_share = market_value / participants
        # if the market share is less than the reward for a transaction
        if market_share < 1:
            return
        # for each participant 
        for i in self.all_hellos.keys():
            enode = gen_enode(i)
            tickets_allowed = len(self.all_hellos[i]) // market_share
            tickets_owned= self.lottery.count(enode)
            # increase or decrease there tickets proportional to theire owned market share
            # make sure they never have less than one ticket
            while tickets_owned < tickets_allowed:
                self.lottery.append(enode)
                tickets_owned += 1
            while tickets_owned > tickets_allowed and tickets_owned > 1:
                self.lottery.remove(enode)
                tickets_owned -= 1
                
    def hello_fixed(self):
        
        # for each participant 
        for i in self.all_hellos.keys():
            enode = gen_enode(i)
            tickets_allowed = len(self.all_hellos[i]) // 10
            tickets_owned= self.lottery.count(enode)
            # increase or decrease there tickets proportional to theire owned market share
            # make sure they never have less than one ticket
            while tickets_owned < tickets_allowed:
                self.lottery.append(enode)
                tickets_owned += 1
            while tickets_owned > tickets_allowed and tickets_owned > 1:
                self.lottery.remove(enode)
                tickets_owned -= 1
                
    def hello_fixed_last(self,block):
        timestamp = block.timestamp
        decay = 200
        # for each participant 
        for i in self.all_hellos.keys():
            enode = gen_enode(i)
            valid_hellos = [e for e in self.all_hellos[i] if e[1] > timestamp - decay]
            tickets_allowed = len(valid_hellos) // 2
            #print(f"ID:{enode} allowed:{len(valid_hellos)}")
            tickets_owned= self.lottery.count(enode)
            # increase or decrease there tickets proportional to theire owned market share
            # make sure they never have less than one ticket
            while tickets_owned < tickets_allowed:
                self.lottery.append(enode)
                tickets_owned += 1
            while tickets_owned > tickets_allowed and tickets_owned > 1:
                self.lottery.remove(enode)
                tickets_owned -= 1
    
    def none(self):
        pass
    