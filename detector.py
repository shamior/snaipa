import config

addLiquidity = '0xe8e33700'
addLiquidityETH = '0xf305d719'
finalize = '0x4bb278f3'
token_lower = config.TOKEN.lower()[2:]

               
unlock_swap = '0xc9567bf9'
possible_wallets = [
]


def detect(tx):                       
    method = tx['input'][:10]
    if method == addLiquidity or method == addLiquidityETH:
        #verifica se eh a token
        if token_lower in tx['input']:
            return tx['gasPrice']
    elif method == finalize:
        #verifica from
        if tx['from'].lower() in possible_wallets:
            return tx['gasPrice']
    if method == unlock_swap:
        if tx['from'].lower() in possible_wallets:
            return tx['gasPrice']
    return 0