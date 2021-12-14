# @phunkstats

Phunk twitter bot reporting stats, bids, etc.

## Getting started

### Requirements

The different bot tasks require different APIs/services, but in order to fully run the bot you'll need the following:

1. [Twitter Developer](https://developer.twitter.com) used to tweet and follow other accounts' tweets
2. [Etherscan API](https://etherscan.io/apis) to fetch and store ABIs for different contracts
3. [Alchemy](https://www.alchemy.com/), [Infura](https://infura.io/) or similar to interact with ethereum node
   via `web3` package
4. ~~Covalent~~ [Moralis](https://moralis.io/) to fetch aggregated NFT data like unique holders

Apart from these, the bot uses `Python 3.9.9` and I recommend using `pyenv` or similar for virtual environment
management.

### Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install all dependencies in one go:

```bash
pip install -r requirements.txt
```

### Usage

Copy `.env.template` into `.env` and add all relevant environment variables.

To run the different tasks you can do:

```shell
# Track new Phunk bids:
python -m tasks.track_bids
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

CC0 — Do what you want
