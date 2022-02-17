from web3.main import Web3
from swap import Swapper
from os import system
import time

import config
import address


swapper = Swapper()

class text:
    green = '\033[92m'
    red = '\033[91m'
    yellow = '\033[93m'
    end = '\033[0m'



def out():
    input('\nPressione enter para sair')
    exit()

def colored_text(color, msg):
    return f"{color}{msg}{text.end}"



def approve_token():
    approve_str = ''
    print("\nTrying to approve the token...")
    approval = swapper.approve(swapper.address['token'])
    if approval['status']:
        if approval['tx_hash']:
            approve_str = colored_text(text.green, 'Approval Sucess!')
            approve_str += f"\nHash: {approval['tx_hash']}\n"
        else:
            approve_str = colored_text(text.green, 'Already Approved!\n')
        print(approve_str)
    else:
        print(colored_text(text.red, "Approve Fail!"))
        out()
    return approve_str

def buy():
    ##buy part
    print('Trying to buy...')
    before = time.perf_counter()
    if config.PAIRED_WITH == address.BNB:
        txn = swapper.swapExactBNBForTokens(
            int(config.AMOUNT*10**18),
            swapper.gas
        )
    else:
        txn = swapper.swapExactTokensForTokens(
            int(config.AMOUNT*10**18),
            config.PAIRED_WITH,
            config.TOKEN,
            swapper.gas
        )
    after = time.perf_counter()
    time_taken = after-before
    return time_taken, txn

def log_buy(time_taken, txn):
    if txn['status']:
        txn_str = f"{colored_text(text.green, 'Transaction Success!')}"
        txn_str += f"\nTime Taken: {time_taken:.3f} secs"
        txn_str += f"\nHash: {txn['tx_hash']}"
        print(txn_str)
        time.sleep(3)
        balance = swapper.tkn_contract.functions.balanceOf(config.WALLET).call()
        amount_in = config.AMOUNT
        if config.PAIRED_WITH == address.BNB:
            amount_in *= swapper.get_bnb_price()
        
        price_bought = amount_in/(balance*10**-swapper.decimals)
        bought_str =  colored_text(text.yellow, f'\n\nPrice Bought: {price_bought:.12f}')
        bought_str += f"\nAmount Bought: {balance:.12f}"
        cur_log = txn_str + bought_str
        system('clear')
        print(cur_log)
        target = config.TARGET*price_bought
        cur_price = swapper.get_token_price(config.TOKEN)
        target_str = f"\nTarget Price: {target:.12f}\n"
        cur_log = cur_log + target_str
        cur_price_str = f"Current Price: {cur_price:.12f}\n"
        system('clear')
        print(cur_log + cur_price_str)
    else:
        print(colored_text(text.red, "Transaction Failed!"))
        print(f'Time Taken: {time_taken:.3f} secs')
        print(f'Hash: {txn["tx_hash"]}')
        out()
    return cur_log, target, balance

def wait_for_target(cur_log, target):
    cur_price = -1
    while cur_price < target:
        cur_price = swapper.get_token_price(swapper.address['token'])
        cur_price_str = f"Current Price: {cur_price:.9f}\n"
        system('clear')
        print(cur_log + cur_price_str)
    print(colored_text(text.green, 'Target Reached!'))

def sell(balance):
    print('Trying to sell...')
    satisfied = False
    if config.PAIRED_WITH == address.BNB:
        balance_before = swapper.w3.eth.get_balance(config.WALLET)*10**-18
    else:
        balance_before = swapper.coin_stable_contract.functions.balanceOf(config.WALLET).call()*10**-18
    while not satisfied:
        before = time.perf_counter()
        if config.PAIRED_WITH == address.BNB:
            txn = swapper.swapExactTokensForBNB(
                balance,
                6*10**9
            )
        else:
            txn = swapper.swapExactTokensForTokens(
                balance,
                config.TOKEN,
                config.PAIRED_WITH,
                6*10**9
            )
        after = time.perf_counter()
        time_taken = after - before
        if txn['status']:
            satisfied = True
            txn_str_sell = f"\n{colored_text(text.green, 'Transaction Success!')}"
            txn_str_sell += f"\nTime Taken: {time_taken:.3f} secs"
            txn_str_sell += f"\nHash: {txn['tx_hash']}"
            print(txn_str_sell)
            time.sleep(3)
            if config.PAIRED_WITH == address.BNB:
                balance_after = swapper.w3.eth.get_balance(config.WALLET)*10**-18
            else:
                balance_after = swapper.coin_stable_contract.functions.balanceOf(config.WALLET).call()*10**-18
            
            price_sold = (balance*10**-swapper.decimals)/(balance_after-balance_before)
            print(colored_text(text.yellow, f"Price Sold: {price_sold:.12f}"))
        else:
            print(colored_text(text.red, "Transaction Failed!"))
            print(f'Time Taken: {time_taken:.3f} secs')
            print(f'Hash: {txn["tx_hash"]}')
            answer = input('Try again (y/n): ')
            satisfied = answer.lower() != 'y'
    out()



approve_token()
swapper.wait_for_green_light()
print(colored_text(text.green, 'Tx Found!!'))
time_taken, txn = buy()
cur_log, target, balance = log_buy(time_taken, txn)
wait_for_target(cur_log, target)
sell()








