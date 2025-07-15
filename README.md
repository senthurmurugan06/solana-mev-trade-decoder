# Solana MEV Trade Decoder

A Python tool to fetch, decode, and analyze recent Solana transactions for MEV (Maximal Extractable Value) patterns such as arbitrage and backruns.

## Features
- Fetches recent Solana transactions via Helius API
- Decodes trades, wallets, platforms, and profit
- Detects MEV patterns: backrun, arbitrage, etc.
- Outputs a summary for each transaction

## Installation
1. Clone the repository or download the script.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Set your Helius API key as an environment variable:
   ```bash
   export HELIUS_API_KEY=your_helius_api_key
   ```
   Or edit the script to hardcode your API key.

## Usage
Run the script to fetch and analyze recent transactions for the Jupiter Aggregator program:

```bash
python solana_mev_decoder.py
```

Example output:
```
{'tx': '5JqK3...d9f',
 'wallet': '9xyz...Abc',
 'path': 'USDC → SOL → mSOL',
 'platforms': ['Jupiter', 'Meteora'],
 'profit': '0.39 USDC',
 'is_mev': True,
 'pattern': 'Backrun of user swap at same slot'}
```

## Customization
- To analyze a different program, change the `PROGRAM_ADDRESS` in the script.
- Extend token and DEX mappings in the script for broader coverage.
- For a live dashboard, see the Streamlit example in the script and install `streamlit`.

## License
MIT 