import requests
import os

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "31fda625-8ca5-4977-b4f9-ef50d85a2236")
HELIUS_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

TOKEN_MAP = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "So11111111111111111111111111111111111111112": "SOL",
    "mSoLzCrK6KrAEFq3Q7t8k8k8k8k8k8k8k8k8k8k8k8k8": "mSOL",
    "Es9vMFrzaCER9sQF2Q8k4p8p8nH3c7Yw2Zrjz5kF3bG9": "USDT",
    "SHDW1v14ZrQ8Xk1r5qk8k8k8k8k8k8k8k8k8k8k8k8k8": "SHDW",
    "native": "SOL"
}

PROGRAM_ID_MAP = {
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter",
    "METEoRA9dFZz5e6h8vLwYp6kQw6r1t4QKq5k3h8vLwYp": "Meteora",
    "4ckmDgGzLYLyEcdh5uM4a5hQKx1e5gn9wQw5G6XcE9E5": "Raydium"
}

def get_recent_signatures(address, limit=10):
    url = HELIUS_ENDPOINT
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [address, {"limit": limit}]
    }
    response = requests.post(url, json=payload)
    data = response.json()
    print("API response:", data)
    return [tx["signature"] for tx in data.get("result", [])]

def get_transaction_details(signature):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
    }
    response = requests.post(HELIUS_ENDPOINT, json=payload)
    return response.json().get("result", {})

def extract_trade_info(tx_data):
    instructions = tx_data.get("transaction", {}).get("message", {}).get("instructions", [])
    meta = tx_data.get("meta", {})
    platforms = set()
    for instr in instructions:
        program_id = instr.get("programId")
        if program_id in PROGRAM_ID_MAP:
            platforms.add(PROGRAM_ID_MAP[program_id])
    trade_path = []
    pre_bal = meta.get("preTokenBalances", [])
    post_bal = meta.get("postTokenBalances", [])
    for i in range(len(pre_bal)):
        pre = pre_bal[i]["uiTokenAmount"]["uiAmount"]
        post = post_bal[i]["uiTokenAmount"]["uiAmount"]
        if pre is None:
            pre = 0.0
        if post is None:
            post = 0.0
        mint = pre_bal[i]["mint"]
        symbol = TOKEN_MAP.get(mint, mint[:4] + "..." + mint[-4:])
        if pre > post:
            trade_path.append(symbol)
        elif post > pre:
            trade_path.append(symbol)
    inner = meta.get("innerInstructions", [])
    for inner_ix in inner:
        for ix in inner_ix.get("instructions", []):
            program_id = ix.get("programId")
            if program_id in PROGRAM_ID_MAP:
                platforms.add(PROGRAM_ID_MAP[program_id])
            accounts = ix.get("accounts", [])
            for acc in accounts:
                symbol = TOKEN_MAP.get(acc, acc[:4] + "..." + acc[-4:])
                if symbol not in trade_path:
                    trade_path.append(symbol)
    seen = set()
    trade_path_unique = []
    for t in trade_path:
        if t not in seen:
            trade_path_unique.append(t)
            seen.add(t)
    return trade_path_unique, list(platforms)

def estimate_usdc_profit(pre_balances, post_balances, token_prices):
    profit = 0.0
    for mint, pre in pre_balances.items():
        post = post_balances.get(mint, 0)
        delta = post - pre
        price = token_prices.get(mint, 0)
        profit += delta * price
    return profit

def detect_mev(tx_data, trade_path, platforms, profit):
    logs = tx_data.get("meta", {}).get("logMessages", [])
    slot = tx_data.get("slot", None)
    if len(platforms) > 1 and profit > 0.0:
        return True, "Multi-venue arbitrage"
    for log in logs:
        if "backrun" in log.lower():
            return True, "Backrun detected in logs"
    if profit > 0.0:
        return True, "Profitable trade"
    return False, None

def summarize_transaction(signature):
    tx_data = get_transaction_details(signature)
    trade_path, platforms = extract_trade_info(tx_data)
    wallet = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [{}])[0].get("pubkey", "N/A")
    pre_bal = tx_data.get("meta", {}).get("preTokenBalances", [])
    post_bal = tx_data.get("meta", {}).get("postTokenBalances", [])
    pre_balances = {b["mint"]: float(b["uiTokenAmount"]["uiAmount"]) if b["uiTokenAmount"]["uiAmount"] is not None else 0.0 for b in pre_bal}
    post_balances = {b["mint"]: float(b["uiTokenAmount"]["uiAmount"]) if b["uiTokenAmount"]["uiAmount"] is not None else 0.0 for b in post_bal}
    token_prices = {
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 1.0,
        "So11111111111111111111111111111111111111112": 150.0,
        "mSoLzCrK6KrAEFq3Q7t8k8k8k8k8k8k8k8k8k8k8k8k8": 150.0,
        "Es9vMFrzaCER9sQF2Q8k4p8p8nH3c7Yw2Zrjz5kF3bG9": 1.0
    }
    profit = estimate_usdc_profit(pre_balances, post_balances, token_prices)
    is_mev, pattern = detect_mev(tx_data, trade_path, platforms, profit)
    profit_str = f"{profit:.2f} USDC" if profit == 0.0 else f"{profit:.4f} USDC"
    return {
        "tx": signature,
        "wallet": wallet,
        "path": " → ".join(trade_path),
        "platforms": platforms,
        "profit": profit_str,
        "is_mev": is_mev,
        "pattern": pattern if pattern else "N/A"
    }

if __name__ == "__main__":
    PROGRAM_ADDRESS = "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB"
    signatures = get_recent_signatures(PROGRAM_ADDRESS, limit=5)
    print("Signatures:", signatures)
    for sig in signatures:
        summary = summarize_transaction(sig)
        print(summary) 