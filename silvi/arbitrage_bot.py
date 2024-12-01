import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage.log'),
        logging.StreamHandler()
    ]
)

class ArbitrageFinder:
    def __init__(self):
        self.api_keys = {
            'pinnacle': os.getenv('PINNACLE_API_KEY'),
            'betfair': os.getenv('BETFAIR_API_KEY'),
            'bet365': os.getenv('BET365_API_KEY'),
            'draftkings': os.getenv('DRAFTKINGS_API_KEY'),
            'fanduel': os.getenv('FANDUEL_API_KEY'),
            'williamhill': os.getenv('WILLIAMHILL_API_KEY')
        }
        self.min_profit_threshold = float(os.getenv('MIN_PROFIT_THRESHOLD', '1.0'))
        self.max_stake = float(os.getenv('MAX_STAKE', '100.0'))

    def get_odds_pinnacle(self, sport: str) -> List[Dict]:
        """Fetch odds from Pinnacle Sports API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["pinnacle"]}',
                'Accept': 'application/json'
            }
            # Pinnacle API v1 endpoint for sports odds
            response = requests.get(
                'https://api.pinnacle.com/v2/odds',
                params={'sportId': self._get_sport_id(sport).get('pinnacle'), 'oddsFormat': 'DECIMAL'},
                headers=headers
            )
            response.raise_for_status()
            return response.json().get('leagues', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching Pinnacle odds: {e}")
            return []

    def get_odds_betfair(self, sport: str) -> List[Dict]:
        """Fetch odds from Betfair Exchange API"""
        try:
            headers = {
                'X-Application': self.api_keys["betfair"],
                'X-Authentication': os.getenv('BETFAIR_SESSION_TOKEN'),
                'Accept': 'application/json'
            }
            # First get event IDs for the sport
            response = requests.post(
                'https://api.betfair.com/exchange/betting/rest/v1.0/listEvents/',
                headers=headers,
                json={"filter": {"textQuery": sport}}
            )
            response.raise_for_status()
            events = response.json()
            
            all_odds = []
            for event in events:
                # Then get odds for each event
                market_response = requests.post(
                    'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/',
                    headers=headers,
                    json={"marketIds": [event['marketId']]}
                )
                if market_response.status_code == 200:
                    all_odds.extend(market_response.json())
            
            return all_odds
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching Betfair odds: {e}")
            return []

    def _get_sport_id(self, sport: str) -> Dict:
        """Convert sport name to ID for various bookmakers"""
        sport_ids = {
            'football': {
                'pinnacle': 29,
                'betfair': 1,
                'draftkings': 'NFL',
                'fanduel': 'american-football'
            },
            'tennis': {
                'pinnacle': 33,
                'betfair': 2,
                'draftkings': 'TENNIS',
                'fanduel': 'tennis'
            },
            'basketball': {
                'pinnacle': 4,
                'betfair': 7522,
                'draftkings': 'NBA',
                'fanduel': 'basketball'
            }
        }
        return sport_ids.get(sport.lower(), {})

    def get_odds_draftkings(self, sport: str) -> List[Dict]:
        """Fetch odds from DraftKings API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["draftkings"]}',
                'Accept': 'application/json'
            }
            sport_id = self._get_sport_id(sport).get('draftkings')
            response = requests.get(
                f'https://api.draftkings.com/sites/US-SB/sports/{sport_id}/odds',
                headers=headers
            )
            response.raise_for_status()
            return response.json().get('events', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching DraftKings odds: {e}")
            return []

    def get_odds_fanduel(self, sport: str) -> List[Dict]:
        """Fetch odds from FanDuel API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["fanduel"]}',
                'Accept': 'application/json'
            }
            sport_id = self._get_sport_id(sport).get('fanduel')
            response = requests.get(
                f'https://sportsbook.fanduel.com/api/content-service/v2/sports/{sport_id}/events',
                headers=headers
            )
            response.raise_for_status()
            return response.json().get('events', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching FanDuel odds: {e}")
            return []

    def get_odds_williamhill(self, sport: str) -> List[Dict]:
        """Fetch odds from William Hill API"""
        try:
            headers = {'Authorization': f'Bearer {self.api_keys["williamhill"]}'}
            response = requests.get(
                'https://api.williamhill.com/v1/odds',
                params={'sport': sport},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching William Hill odds: {e}")
            return []

    def calculate_arbitrage(self, odds1: float, odds2: float) -> Tuple[bool, float, Dict[str, float]]:
        """
        Calculate if there's an arbitrage opportunity between two odds
        Returns: (is_arbitrage, profit_percentage, stake_distribution)
        """
        inv_sum = (1 / odds1) + (1 / odds2)
        profit_percentage = (1 - inv_sum) * 100

        if profit_percentage > self.min_profit_threshold:
            # Calculate optimal stake distribution
            total_stake = min(self.max_stake, 1000)  # Limit maximum stake
            stake1 = total_stake * (1 / odds1) / inv_sum
            stake2 = total_stake * (1 / odds2) / inv_sum
            
            return True, profit_percentage, {
                'total_stake': total_stake,
                'stake1': stake1,
                'stake2': stake2,
                'potential_profit': total_stake * (profit_percentage / 100)
            }
        
        return False, profit_percentage, {}

    def place_bet_pinnacle(self, bet_details: Dict) -> bool:
        """Place a bet on Pinnacle"""
        try:
            headers = {'Authorization': f'Bearer {self.api_keys["pinnacle"]}'}
            response = requests.post(
                'https://api.pinnacle.com/v1/bets/place',
                json=bet_details,
                headers=headers
            )
            response.raise_for_status()
            logging.info(f"Bet placed successfully on Pinnacle: {bet_details}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error placing bet on Pinnacle: {e}")
            return False

    def place_bet_betfair(self, bet_details: Dict) -> bool:
        """Place a bet on Betfair"""
        try:
            headers = {
                'X-Application': self.api_keys["betfair"],
                'X-Authentication': os.getenv('BETFAIR_SESSION_TOKEN'),
                'Accept': 'application/json'
            }
            response = requests.post(
                'https://api.betfair.com/exchange/betting/rest/v1.0/placeOrders',
                json=bet_details,
                headers=headers
            )
            response.raise_for_status()
            logging.info(f"Bet placed successfully on Betfair: {bet_details}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error placing bet on Betfair: {e}")
            return False

    def place_bet_draftkings(self, bet_details: Dict) -> bool:
        """Place a bet on DraftKings"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["draftkings"]}',
                'Accept': 'application/json'
            }
            response = requests.post(
                'https://api.draftkings.com/v1/bets/place',
                json=bet_details,
                headers=headers
            )
            response.raise_for_status()
            logging.info(f"Bet placed successfully on DraftKings: {bet_details}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error placing bet on DraftKings: {e}")
            return False

    def place_bet_fanduel(self, bet_details: Dict) -> bool:
        """Place a bet on FanDuel"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["fanduel"]}',
                'Accept': 'application/json'
            }
            response = requests.post(
                'https://api.fanduel.com/v1/bets/place',
                json=bet_details,
                headers=headers
            )
            response.raise_for_status()
            logging.info(f"Bet placed successfully on FanDuel: {bet_details}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error placing bet on FanDuel: {e}")
            return False

    def place_bet_williamhill(self, bet_details: Dict) -> bool:
        """Place a bet on William Hill"""
        try:
            headers = {'Authorization': f'Bearer {self.api_keys["williamhill"]}'}
            response = requests.post(
                'https://api.williamhill.com/v1/bets/place',
                json=bet_details,
                headers=headers
            )
            response.raise_for_status()
            logging.info(f"Bet placed successfully on William Hill: {bet_details}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error placing bet on William Hill: {e}")
            return False

    def find_opportunities(self, sport: str) -> List[Dict]:
        """Find arbitrage opportunities for a given sport"""
        opportunities = []
        
        # Fetch odds from different bookmakers
        pinnacle_odds = self.get_odds_pinnacle(sport)
        betfair_odds = self.get_odds_betfair(sport)
        draftkings_odds = self.get_odds_draftkings(sport)
        fanduel_odds = self.get_odds_fanduel(sport)
        williamhill_odds = self.get_odds_williamhill(sport)
        
        # Compare odds for each matching event
        for p_event in pinnacle_odds:
            for b_event in betfair_odds:
                if self._is_same_event(p_event, b_event):
                    # Check each market combination
                    for p_market in p_event['markets']:
                        for b_market in b_event['markets']:
                            if self._is_matching_market(p_market, b_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(p_market['odds']),
                                    float(b_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': p_event['event'],
                                        'market': p_market['name'],
                                        'bookmaker1': {
                                            'name': 'Pinnacle',
                                            'odds': p_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'Betfair',
                                            'odds': b_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for p_event in pinnacle_odds:
            for d_event in draftkings_odds:
                if self._is_same_event(p_event, d_event):
                    # Check each market combination
                    for p_market in p_event['markets']:
                        for d_market in d_event['markets']:
                            if self._is_matching_market(p_market, d_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(p_market['odds']),
                                    float(d_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': p_event['event'],
                                        'market': p_market['name'],
                                        'bookmaker1': {
                                            'name': 'Pinnacle',
                                            'odds': p_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'DraftKings',
                                            'odds': d_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for p_event in pinnacle_odds:
            for f_event in fanduel_odds:
                if self._is_same_event(p_event, f_event):
                    # Check each market combination
                    for p_market in p_event['markets']:
                        for f_market in f_event['markets']:
                            if self._is_matching_market(p_market, f_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(p_market['odds']),
                                    float(f_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': p_event['event'],
                                        'market': p_market['name'],
                                        'bookmaker1': {
                                            'name': 'Pinnacle',
                                            'odds': p_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'FanDuel',
                                            'odds': f_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for p_event in pinnacle_odds:
            for w_event in williamhill_odds:
                if self._is_same_event(p_event, w_event):
                    # Check each market combination
                    for p_market in p_event['markets']:
                        for w_market in w_event['markets']:
                            if self._is_matching_market(p_market, w_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(p_market['odds']),
                                    float(w_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': p_event['event'],
                                        'market': p_market['name'],
                                        'bookmaker1': {
                                            'name': 'Pinnacle',
                                            'odds': p_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'William Hill',
                                            'odds': w_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for b_event in betfair_odds:
            for d_event in draftkings_odds:
                if self._is_same_event(b_event, d_event):
                    # Check each market combination
                    for b_market in b_event['markets']:
                        for d_market in d_event['markets']:
                            if self._is_matching_market(b_market, d_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(b_market['odds']),
                                    float(d_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': b_event['event'],
                                        'market': b_market['name'],
                                        'bookmaker1': {
                                            'name': 'Betfair',
                                            'odds': b_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'DraftKings',
                                            'odds': d_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for b_event in betfair_odds:
            for f_event in fanduel_odds:
                if self._is_same_event(b_event, f_event):
                    # Check each market combination
                    for b_market in b_event['markets']:
                        for f_market in f_event['markets']:
                            if self._is_matching_market(b_market, f_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(b_market['odds']),
                                    float(f_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': b_event['event'],
                                        'market': b_market['name'],
                                        'bookmaker1': {
                                            'name': 'Betfair',
                                            'odds': b_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'FanDuel',
                                            'odds': f_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for b_event in betfair_odds:
            for w_event in williamhill_odds:
                if self._is_same_event(b_event, w_event):
                    # Check each market combination
                    for b_market in b_event['markets']:
                        for w_market in w_event['markets']:
                            if self._is_matching_market(b_market, w_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(b_market['odds']),
                                    float(w_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': b_event['event'],
                                        'market': b_market['name'],
                                        'bookmaker1': {
                                            'name': 'Betfair',
                                            'odds': b_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'William Hill',
                                            'odds': w_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for d_event in draftkings_odds:
            for f_event in fanduel_odds:
                if self._is_same_event(d_event, f_event):
                    # Check each market combination
                    for d_market in d_event['markets']:
                        for f_market in f_event['markets']:
                            if self._is_matching_market(d_market, f_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(d_market['odds']),
                                    float(f_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': d_event['event'],
                                        'market': d_market['name'],
                                        'bookmaker1': {
                                            'name': 'DraftKings',
                                            'odds': d_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'FanDuel',
                                            'odds': f_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for d_event in draftkings_odds:
            for w_event in williamhill_odds:
                if self._is_same_event(d_event, w_event):
                    # Check each market combination
                    for d_market in d_event['markets']:
                        for w_market in w_event['markets']:
                            if self._is_matching_market(d_market, w_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(d_market['odds']),
                                    float(w_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': d_event['event'],
                                        'market': d_market['name'],
                                        'bookmaker1': {
                                            'name': 'DraftKings',
                                            'odds': d_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'William Hill',
                                            'odds': w_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        
        for f_event in fanduel_odds:
            for w_event in williamhill_odds:
                if self._is_same_event(f_event, w_event):
                    # Check each market combination
                    for f_market in f_event['markets']:
                        for w_market in w_event['markets']:
                            if self._is_matching_market(f_market, w_market):
                                is_arb, profit, stakes = self.calculate_arbitrage(
                                    float(f_market['odds']),
                                    float(w_market['odds'])
                                )
                                
                                if is_arb:
                                    opportunities.append({
                                        'event': f_event['event'],
                                        'market': f_market['name'],
                                        'bookmaker1': {
                                            'name': 'FanDuel',
                                            'odds': f_market['odds'],
                                            'stake': stakes['stake1']
                                        },
                                        'bookmaker2': {
                                            'name': 'William Hill',
                                            'odds': w_market['odds'],
                                            'stake': stakes['stake2']
                                        },
                                        'profit_percentage': profit,
                                        'potential_profit': stakes['potential_profit'],
                                        'timestamp': datetime.now().isoformat()
                                    })
        return opportunities

    def execute_arbitrage(self, opportunity: Dict) -> bool:
        """Execute the arbitrage opportunity by placing bets"""
        bookmaker1 = opportunity['bookmaker1']['name'].lower()
        bookmaker2 = opportunity['bookmaker2']['name'].lower()
        
        # Place first bet
        bet1_success = False
        if hasattr(self, f'place_bet_{bookmaker1}'):
            bet1_success = getattr(self, f'place_bet_{bookmaker1}')({
                'event': opportunity['event'],
                'market': opportunity['market'],
                'odds': opportunity['bookmaker1']['odds'],
                'stake': opportunity['bookmaker1']['stake']
            })
        
        if not bet1_success:
            logging.error(f"Failed to place first bet with {bookmaker1}, aborting arbitrage")
            return False
        
        # Place second bet
        bet2_success = False
        if hasattr(self, f'place_bet_{bookmaker2}'):
            bet2_success = getattr(self, f'place_bet_{bookmaker2}')({
                'event': opportunity['event'],
                'market': opportunity['market'],
                'odds': opportunity['bookmaker2']['odds'],
                'stake': opportunity['bookmaker2']['stake']
            })
        
        if not bet2_success:
            logging.error(f"Failed to place second bet with {bookmaker2}, attempting to cancel first bet")
            # Here you would implement bet cancellation logic for the first bet
            return False
        
        logging.info(f"Successfully executed arbitrage opportunity: {opportunity}")
        return True

def main():
    finder = ArbitrageFinder()
    while True:
        try:
            # Monitor popular sports
            sports = ['football', 'tennis', 'basketball']
            for sport in sports:
                opportunities = finder.find_opportunities(sport)
                for opportunity in opportunities:
                    logging.info(f"Found opportunity: {opportunity}")
                    if opportunity['profit_percentage'] >= finder.min_profit_threshold:
                        finder.execute_arbitrage(opportunity)
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait longer if there's an error

if __name__ == "__main__":
    main()
