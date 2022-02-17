from web3 import Web3
from web3 import exceptions as w3_expts
import json
import time
import concurrent.futures as ftr
from functools import partial
from threading import Thread, Lock
import math

from eth_typing.evm import ChecksumAddress
from web3.types import Wei

##locals
import address
import config
import secret
import detector

locker = Lock()
socket_index = 0
sockets_amount = len(secret.PROVIDERS)

def get_socket_index():
    global socket_index
    locker.acquire()
    index = socket_index
    socket_index += 1
    if socket_index >= sockets_amount:
        socket_index = 0
    locker.release()
    return index
    

class Swapper():
    def __init__(self):
        self.w3 =  self.connect_to_node("wss://speedy-nodes-nyc.moralis.io/f15b03171b2f5127ed2511ef/bsc/mainnet/ws")
        self.abis = {
            "pancake": self.get_abi('./abi/ps_abi.json'),
            "bep20": self.get_abi('./abi/bep20_abi_token.json'),
            "pancake_factory": self.get_abi('./abi/ps_factory_abi.json')
        }
        self.owner_wallet = ''
        self.gas = 0

        self.ps_contract = self.w3.eth.contract(
            address= address.ROUTER,
            abi=self.abis['pancake']
        )
        self.tkn_contract = self.w3.eth.contract(
            address=config.TOKEN,
            abi=self.abis['bep20']
        )
        self.decimals = self.tkn_contract.functions.decimals().call()

        self.coin_stable_contract = self.w3.eth.contract(
            address=config.PAIRED_WITH,
            abi=self.abis['bep20']
        )
        self.ps_factory_contract = self.w3.eth.contract(
            address=address.FACTORY,
            abi=self.abis['pancake_factory']
        )
    def get_token_price(self, token: ChecksumAddress, paired_with: ChecksumAddress, decimals: int):
        price = self.ps_contract.functions.getAmountsOut(
            10**decimals, [token, paired_with]
        ).call()[1]
        price *= 10**-decimals
        if decimals != 18:
            price *= 10**-(18-decimals)
        if paired_with == address.BNB:
            price *= self.ps_contract.functions.getAmountsOut(
                10**18, [address.BNB, address.BUSD]
            ).call()[1]*10**-18
        return price
    def get_bnb_price(self):
        return self.ps_contract.functions.getAmountsOut(
            10**18, [address.BNB, address.BUSD]
        ).call()[1]*10**-18       
    def get_abi(self, abi_path: str):
        with open(abi_path) as file:
            return json.load(file)
    def swapExactTokensForTokens(self, amountIn:Wei, frm:ChecksumAddress, to:ChecksumAddress, gwei:Wei):
        amountOutMin = int(0.000001e18)
        #Function: swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline)
        tx = self.ps_contract.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(
            amountIn,                   #amountIn
            amountOutMin,               #amountOutMin
            [                           #path
                frm,                    #
                to                      #
            ],                          #
            config.WALLET,              #to
            int(time.time()+60)         #deadline
        ).buildTransaction(
            {
                'from': config.WALLET,
                'gas': config.GAS,
                'gasPrice': gwei,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET)
            }
        )
        tx_hash = self.w3.eth.send_raw_transaction(
            self.w3.eth.account.sign_transaction(
                tx,
                private_key=secret.PRIVATE_KEY
            ).rawTransaction
        ).hex()
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        tx_status = receipt['status'] == 1
        return {
            "status": tx_status,
            "tx_hash": tx_hash
        }
    def swapExactBNBForTokens(self, amountIn:Wei, gwei:Wei):
        amountOutMin = int(0.00001e18)
        #swapExactETHForTokens(uint256 amountOutMin, address[] path, address to, uint256 deadline)
        tx = self.ps_contract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
            amountOutMin,               #amountOutMin
            [                           #path
                address.BNB,            #
                config.TOKEN            #
            ],                          #
            config.WALLET,              #to
            int(time.time()+60)         #deadline
        ).buildTransaction(
            {
                'from': config.WALLET,
                'value': amountIn,
                'gas': config.GAS,
                'gasPrice': gwei,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET)
            }
        )
        tx_hash = self.w3.eth.send_raw_transaction(
            self.w3.eth.account.sign_transaction(
                tx,
                private_key=secret.PRIVATE_KEY
            ).rawTransaction
        ).hex()
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        tx_status = receipt['status'] == 1
        return {
            "status": tx_status,
            "tx_hash": tx_hash
        }
    def swapExactTokensForBNB(self, amountIn:Wei, gwei:Wei):
        #Function: swapExactTokensForETH(uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline)
        amountOutMin = int(0.000001e18)

        tx = self.ps_contract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
            amountIn,                               #amountIn
            amountOutMin,                           #amountOutMin
            [                                       #path
                config.TOKEN,                       #
                address.BNB                         #
            ],                                      #
            config.WALLET,                          #to
            int(time.time()+60)                     #deadline
        ).buildTransaction(
            {
                'from': config.WALLET,
                'gas': config.GAS,
                'gasPrice': gwei,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET)
            }
        )
        tx_hash = self.w3.eth.send_raw_transaction(
            self.w3.eth.account.sign_transaction(
                tx,
                private_key=secret.PRIVATE_KEY
            ).rawTransaction
        ).hex()
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        tx_status = receipt['status'] == 1
        return {
            "status": tx_status,
            "tx_hash": tx_hash,
        }
    def approve(self, token:ChecksumAddress):
        token_contract = self.w3.eth.contract(
            address=token,
            abi=self.abis['bep20']
        )
        allowed = token_contract.functions.allowance(
            config.WALLET,
            address.ROUTER
        ).call()
        if not allowed:
            tx = token_contract.functions.approve(
                address.ROUTER,
                0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
            ).buildTransaction(
                {
                    'from': config.WALLET,
                    'gasPrice': 5*10**9,
                    'nonce': self.w3.eth.get_transaction_count(config.WALLET)
                }
            )
            tx_hash = self.w3.eth.send_raw_transaction(
                self.w3.eth.account.sign_transaction(
                    tx,
                    secret.PRIVATE_KEY
                ).rawTransaction
            )
            status = self.w3.eth.wait_for_transaction_receipt(tx_hash)['status'] == 1
            return {
                'status': status,
                'tx_hash': tx_hash.hex()
            }
        else:
            return {
                'status': True,
                'tx_hash': '',
            }
    def handle_task(self, list_of_hashes, sockets):
        for hash in list_of_hashes:
            try:
                index = get_socket_index()
                print(index)
                socket = sockets[index]
                tx_data = socket.eth.get_transaction(hash)
                gas = detector.detect(tx_data)
                if gas:
                    self.event_found = True
                    self.gas = gas
                    break
            except w3_expts.TransactionNotFound:
                pass
    def connect_to_node(self, provider):
        connected = False
        prov = None
        if 'https' in provider:
            prov = Web3.HTTPProvider(provider)
        elif 'wss:' in provider:
            prov = Web3.WebsocketProvider(provider)
        while not connected:
            conexao = Web3(prov)
            connected = conexao.isConnected()
        print(f"Connected to {provider}")
        return conexao
    def wait_for_green_light(self):
        detector.possible_wallets.append(self.get_owner())
        self.event_found = False
        amount_of_providers = len(secret.PROVIDERS)
        num_of_threads = amount_of_providers
        sockets_future = []
        with ftr.ThreadPoolExecutor() as executor:
            for i in range(num_of_threads):
                sockets_future.append(
                    executor.submit(
                        partial(
                            self.connect_to_node,
                            secret.PROVIDERS[i%amount_of_providers]
                        )
                    )
                )
        sockets = [x.result() for x in ftr.as_completed(sockets_future)]
        pd_filter = sockets[0].eth.filter('pending')
        start = time.perf_counter()
        while not self.event_found:
            loop_time = time.perf_counter()
            list_of_txns = pd_filter.get_new_entries()
            num_of_entries = len(list_of_txns)
            divided_entries = num_of_entries/num_of_threads
            threads = []
            if num_of_entries < num_of_threads:
                for i in range(math.ceil(num_of_entries/2)):
                    threads.append(
                        Thread(
                            target=partial(
                                self.handle_task,
                                list_of_txns[
                                    i*2:(i+1)*2
                                ],
                                sockets
                            )
                        )
                    )
            else:
                for i in range(num_of_threads):
                    threads.append(
                        Thread(
                            target=partial(
                                self.handle_task,
                                list_of_txns[
                                    math.ceil(i*divided_entries):math.ceil((i+1)*divided_entries)
                                ],
                                sockets
                            )
                        )
                    )
            cur_num_threads = len(threads)
            for i in range(cur_num_threads):
                threads[i].start()
            for thread in threads:
                thread.join()
            print(f"Txs: {num_of_entries:<5}\t\tTime to proccess: {time.perf_counter()-loop_time:.3f}s\t\tWaiting time: {time.perf_counter()-start:.3f}s")
            time.sleep(0.5)

            
    def get_owner(self):
        w = self.tkn_contract.functions.owner().call().lower()
        self.owner_wallet = w
        return w
        
        

if __name__ == "__main__":
    s = Swapper()
    while True:
        num = s.w3.eth.get_block_number()
        print(num)
