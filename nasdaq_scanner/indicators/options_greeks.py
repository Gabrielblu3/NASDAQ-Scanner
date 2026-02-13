"""Options Greeks and IV metrics calculations."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.stats import norm


@dataclass
class OptionGreeks:
    """Container for option Greeks."""

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class OptionsGreeks:
    """Calculate option Greeks using Black-Scholes model."""

    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.05  # 5% default risk-free rate

    @staticmethod
    def black_scholes_price(
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float,
        is_call: bool = True,
    ) -> float:
        """
        Calculate Black-Scholes option price.

        Args:
            spot: Current stock price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (decimal)
            risk_free_rate: Risk-free interest rate (decimal)
            is_call: True for call, False for put

        Returns:
            Option price
        """
        if time_to_expiry <= 0:
            # At expiration
            if is_call:
                return max(0, spot - strike)
            return max(0, strike - spot)

        d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
            volatility * math.sqrt(time_to_expiry)
        )
        d2 = d1 - volatility * math.sqrt(time_to_expiry)

        if is_call:
            price = spot * norm.cdf(d1) - strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
        else:
            price = strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)

        return price

    @staticmethod
    def calculate_greeks(
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05,
        is_call: bool = True,
    ) -> OptionGreeks:
        """
        Calculate all Greeks for an option.

        Args:
            spot: Current stock price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (decimal)
            risk_free_rate: Risk-free interest rate
            is_call: True for call, False for put

        Returns:
            OptionGreeks object with all Greeks
        """
        if time_to_expiry <= 0 or volatility <= 0:
            return OptionGreeks(
                delta=1.0 if is_call and spot > strike else -1.0 if not is_call and spot < strike else 0.0,
                gamma=0.0,
                theta=0.0,
                vega=0.0,
                rho=0.0,
            )

        sqrt_t = math.sqrt(time_to_expiry)
        d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
            volatility * sqrt_t
        )
        d2 = d1 - volatility * sqrt_t

        # PDF of standard normal
        pdf_d1 = norm.pdf(d1)

        # Delta
        if is_call:
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        # Gamma (same for calls and puts)
        gamma = pdf_d1 / (spot * volatility * sqrt_t)

        # Theta (per day)
        theta_part1 = -(spot * pdf_d1 * volatility) / (2 * sqrt_t)
        if is_call:
            theta_part2 = risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
            theta = (theta_part1 - theta_part2) / 365
        else:
            theta_part2 = risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2)
            theta = (theta_part1 + theta_part2) / 365

        # Vega (per 1% move in IV)
        vega = spot * sqrt_t * pdf_d1 / 100

        # Rho (per 1% move in interest rate)
        if is_call:
            rho = strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2) / 100
        else:
            rho = -strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) / 100

        return OptionGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
        )

    @staticmethod
    def calculate_iv_rank(current_iv: float, iv_history: list[float]) -> Optional[float]:
        """
        Calculate IV Rank.

        IV Rank = (Current IV - 52w Low) / (52w High - 52w Low) * 100

        Args:
            current_iv: Current implied volatility
            iv_history: List of historical IV values

        Returns:
            IV Rank (0-100) or None if insufficient data
        """
        if not iv_history or len(iv_history) < 5:
            return None

        iv_low = min(iv_history)
        iv_high = max(iv_history)

        if iv_high == iv_low:
            return 50.0

        rank = ((current_iv - iv_low) / (iv_high - iv_low)) * 100
        return max(0, min(100, rank))

    @staticmethod
    def calculate_iv_percentile(current_iv: float, iv_history: list[float]) -> Optional[float]:
        """
        Calculate IV Percentile.

        IV Percentile = % of days where IV was lower than current

        Args:
            current_iv: Current implied volatility
            iv_history: List of historical IV values

        Returns:
            IV Percentile (0-100) or None if insufficient data
        """
        if not iv_history or len(iv_history) < 5:
            return None

        days_below = sum(1 for iv in iv_history if iv < current_iv)
        return (days_below / len(iv_history)) * 100

    @staticmethod
    def suggest_strike_for_put(
        current_price: float,
        target_delta: float = -0.30,
        volatility: float = 0.30,
        days_to_expiry: int = 30,
    ) -> float:
        """
        Suggest a strike price for a put based on target delta.

        Args:
            current_price: Current stock price
            target_delta: Desired delta (negative for puts, default -0.30)
            volatility: Implied volatility
            days_to_expiry: Days until expiration

        Returns:
            Suggested strike price
        """
        time_to_expiry = days_to_expiry / 365

        # Binary search for strike that gives target delta
        low_strike = current_price * 0.7
        high_strike = current_price * 1.0

        for _ in range(50):  # Max iterations
            mid_strike = (low_strike + high_strike) / 2
            greeks = OptionsGreeks.calculate_greeks(
                spot=current_price,
                strike=mid_strike,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
                is_call=False,
            )

            if abs(greeks.delta - target_delta) < 0.01:
                return round(mid_strike, 2)

            if greeks.delta < target_delta:
                low_strike = mid_strike
            else:
                high_strike = mid_strike

        return round((low_strike + high_strike) / 2, 2)

    @staticmethod
    def analyze_option(
        spot: float,
        strike: float,
        expiry_date: datetime,
        volatility: float,
        is_call: bool = True,
        risk_free_rate: float = 0.05,
    ) -> dict:
        """
        Comprehensive option analysis.

        Args:
            spot: Current stock price
            strike: Option strike price
            expiry_date: Expiration date
            volatility: Implied volatility
            is_call: True for call, False for put
            risk_free_rate: Risk-free rate

        Returns:
            Dictionary with price, Greeks, and analysis
        """
        days_to_expiry = (expiry_date - datetime.now()).days
        time_to_expiry = max(0, days_to_expiry) / 365

        price = OptionsGreeks.black_scholes_price(
            spot, strike, time_to_expiry, volatility, risk_free_rate, is_call
        )
        greeks = OptionsGreeks.calculate_greeks(
            spot, strike, time_to_expiry, volatility, risk_free_rate, is_call
        )

        # Moneyness
        if is_call:
            moneyness = "ITM" if spot > strike else "ATM" if abs(spot - strike) / spot < 0.02 else "OTM"
        else:
            moneyness = "ITM" if spot < strike else "ATM" if abs(spot - strike) / spot < 0.02 else "OTM"

        return {
            "type": "CALL" if is_call else "PUT",
            "strike": strike,
            "spot": spot,
            "days_to_expiry": days_to_expiry,
            "theoretical_price": round(price, 2),
            "moneyness": moneyness,
            "delta": round(greeks.delta, 4),
            "gamma": round(greeks.gamma, 4),
            "theta": round(greeks.theta, 4),
            "vega": round(greeks.vega, 4),
            "rho": round(greeks.rho, 4),
            "implied_volatility": round(volatility * 100, 2),
        }
