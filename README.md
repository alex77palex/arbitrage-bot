An automated system for finding and executing sports arbitrage betting opportunities across multiple bookmakers.

## Features

- Real-time odds monitoring from multiple bookmakers (Pinnacle, Betfair, Bet365)
- Automated arbitrage opportunity detection
- Smart stake calculation for optimal profits
- Automated bet placement
- Logging and monitoring system
- Email alerts for opportunities and executions

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your environment variables:
- Copy `.env.example` to `.env`
- Add your API keys and configuration settings
- Update email settings for alerts

3. Set up API access:
- Register with supported bookmakers
- Generate API keys
- Add keys to `.env` file

## Usage

Run the arbitrage bot:
```bash
python arbitrage_bot.py
```

The bot will:
1. Monitor odds from configured bookmakers
2. Detect arbitrage opportunities
3. Execute trades when profitable opportunities are found
4. Send alerts for successful trades

## Configuration

Edit `.env` file to configure:
- Minimum profit threshold
- Maximum stake per bet
- Email alert settings
- API keys and endpoints

## Logging

Logs are written to `arbitrage.log` and include:
- Arbitrage opportunities found
- Bet executions
- Errors and warnings
- Performance metrics

## Safety Features

- Maximum stake limits
- Profit threshold settings
- Error handling for failed bets
- Automatic bet cancellation on partial execution

## Disclaimer

This bot is for educational purposes only. Be aware that:
- Arbitrage betting may be against some bookmakers' terms of service
- Real money is at risk
- Markets can move quickly, affecting profitability
- Some bookmakers may limit or ban accounts engaging in arbitrage

## Requirements

- Python 3.8+
- Active bookmaker accounts with API access
- Stable internet connection
- Sufficient funds in bookmaker accounts

## Contributing

Feel free to submit issues and pull requests for improvements.
