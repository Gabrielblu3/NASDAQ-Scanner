"""Prediction tracking system for monitoring signal accuracy."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class PredictionStatus(Enum):
    """Status of a prediction."""
    PENDING = "pending"
    WIN = "win"
    LOSS = "loss"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Prediction:
    """A recorded prediction."""
    id: int
    symbol: str
    signal_type: str
    signal_strength: int
    entry_price: float
    suggested_strike: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    created_at: datetime
    expiry_date: Optional[datetime]
    status: PredictionStatus
    outcome_price: Optional[float]
    outcome_date: Optional[datetime]
    profit_pct: Optional[float]
    notes: Optional[str]


class PredictionTracker:
    """Tracks predictions and their outcomes."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize tracker with database path."""
        if db_path is None:
            # Default to data directory in project
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "predictions.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    signal_strength INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    suggested_strike REAL,
                    target_price REAL,
                    stop_loss REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expiry_date TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    outcome_price REAL,
                    outcome_date TIMESTAMP,
                    profit_pct REAL,
                    notes TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol ON predictions(symbol)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON predictions(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON predictions(created_at)
            """)

    def record_signal(
        self,
        symbol: str,
        signal_type: str,
        signal_strength: int,
        entry_price: float,
        suggested_strike: Optional[float] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        expiry_days: int = 30
    ) -> int:
        """
        Record a new prediction.

        Returns the prediction ID.
        """
        expiry_date = datetime.now() + timedelta(days=expiry_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO predictions (
                    symbol, signal_type, signal_strength, entry_price,
                    suggested_strike, target_price, stop_loss, expiry_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, signal_type, signal_strength, entry_price,
                suggested_strike, target_price, stop_loss, expiry_date
            ))
            return cursor.lastrowid

    def check_duplicate(self, symbol: str, signal_type: str, hours: int = 24) -> bool:
        """Check if a similar signal was recorded recently."""
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM predictions
                WHERE symbol = ? AND signal_type = ?
                AND created_at > ? AND status = 'pending'
            """, (symbol, signal_type, cutoff))
            count = cursor.fetchone()[0]
            return count > 0

    def update_outcome(
        self,
        prediction_id: int,
        status: PredictionStatus,
        outcome_price: float,
        notes: Optional[str] = None
    ):
        """Update a prediction with its outcome."""
        with sqlite3.connect(self.db_path) as conn:
            # Get entry price for profit calculation
            cursor = conn.execute(
                "SELECT entry_price, signal_type FROM predictions WHERE id = ?",
                (prediction_id,)
            )
            row = cursor.fetchone()
            if not row:
                return

            entry_price, signal_type = row

            # Calculate profit percentage based on signal type
            if signal_type in ("PUT_OPPORTUNITY", "HEDGE_SIGNAL"):
                # For puts, profit when price goes down
                profit_pct = ((entry_price - outcome_price) / entry_price) * 100
            else:
                # For calls, profit when price goes up
                profit_pct = ((outcome_price - entry_price) / entry_price) * 100

            conn.execute("""
                UPDATE predictions
                SET status = ?, outcome_price = ?, outcome_date = ?,
                    profit_pct = ?, notes = ?
                WHERE id = ?
            """, (
                status.value, outcome_price, datetime.now(),
                profit_pct, notes, prediction_id
            ))

    def check_and_update_predictions(self, price_data: Dict[str, float]):
        """
        Check pending predictions against current prices.
        Updates status if target or stop hit.
        """
        pending = self.get_predictions(status=PredictionStatus.PENDING)

        for pred in pending:
            if pred.symbol not in price_data:
                continue

            current_price = price_data[pred.symbol]

            # Check for PUT signals
            if pred.signal_type in ("PUT_OPPORTUNITY", "HEDGE_SIGNAL"):
                # Win if price drops to target
                if pred.target_price and current_price <= pred.target_price:
                    self.update_outcome(
                        pred.id, PredictionStatus.WIN, current_price,
                        f"Target hit: ${current_price:.2f}"
                    )
                # Loss if price rises to stop
                elif pred.stop_loss and current_price >= pred.stop_loss:
                    self.update_outcome(
                        pred.id, PredictionStatus.LOSS, current_price,
                        f"Stop loss hit: ${current_price:.2f}"
                    )

            # Check for CALL signals
            elif pred.signal_type == "CALL_OPPORTUNITY":
                # Win if price rises to target
                if pred.target_price and current_price >= pred.target_price:
                    self.update_outcome(
                        pred.id, PredictionStatus.WIN, current_price,
                        f"Target hit: ${current_price:.2f}"
                    )
                # Loss if price drops to stop
                elif pred.stop_loss and current_price <= pred.stop_loss:
                    self.update_outcome(
                        pred.id, PredictionStatus.LOSS, current_price,
                        f"Stop loss hit: ${current_price:.2f}"
                    )

            # Check for expiry
            if pred.expiry_date and datetime.now() > pred.expiry_date:
                if pred.status == PredictionStatus.PENDING:
                    self.update_outcome(
                        pred.id, PredictionStatus.EXPIRED, current_price,
                        "Position expired without hitting target or stop"
                    )

    def expire_old_predictions(self):
        """Mark old pending predictions as expired."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE predictions
                SET status = 'expired', outcome_date = CURRENT_TIMESTAMP,
                    notes = 'Auto-expired after expiry date'
                WHERE status = 'pending' AND expiry_date < CURRENT_TIMESTAMP
            """)

    def get_predictions(
        self,
        status: Optional[PredictionStatus] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Prediction]:
        """Get predictions with optional filters."""
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        predictions = []
        for row in rows:
            predictions.append(Prediction(
                id=row['id'],
                symbol=row['symbol'],
                signal_type=row['signal_type'],
                signal_strength=row['signal_strength'],
                entry_price=row['entry_price'],
                suggested_strike=row['suggested_strike'],
                target_price=row['target_price'],
                stop_loss=row['stop_loss'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                expiry_date=datetime.fromisoformat(row['expiry_date']) if row['expiry_date'] else None,
                status=PredictionStatus(row['status']),
                outcome_price=row['outcome_price'],
                outcome_date=datetime.fromisoformat(row['outcome_date']) if row['outcome_date'] else None,
                profit_pct=row['profit_pct'],
                notes=row['notes']
            ))

        return predictions

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall prediction statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM predictions
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Win rate
            wins = status_counts.get('win', 0)
            losses = status_counts.get('loss', 0)
            total_resolved = wins + losses

            win_rate = (wins / total_resolved * 100) if total_resolved > 0 else 0

            # Average profit on wins
            cursor = conn.execute("""
                SELECT AVG(profit_pct) FROM predictions WHERE status = 'win'
            """)
            avg_win = cursor.fetchone()[0] or 0

            # Average loss on losses
            cursor = conn.execute("""
                SELECT AVG(profit_pct) FROM predictions WHERE status = 'loss'
            """)
            avg_loss = cursor.fetchone()[0] or 0

            # Profit factor (gross profits / gross losses)
            cursor = conn.execute("""
                SELECT SUM(profit_pct) FROM predictions WHERE status = 'win'
            """)
            total_profit = cursor.fetchone()[0] or 0

            cursor = conn.execute("""
                SELECT ABS(SUM(profit_pct)) FROM predictions WHERE status = 'loss'
            """)
            total_loss = cursor.fetchone()[0] or 0

            profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

            # Stats by signal type
            cursor = conn.execute("""
                SELECT signal_type,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'win' THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN status = 'loss' THEN 1 ELSE 0 END) as losses
                FROM predictions
                WHERE status IN ('win', 'loss')
                GROUP BY signal_type
            """)

            by_signal_type = {}
            for row in cursor.fetchall():
                signal_type, total, wins, losses = row
                by_signal_type[signal_type] = {
                    'total': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': (wins / total * 100) if total > 0 else 0
                }

            # Recent performance (last 30 days)
            cursor = conn.execute("""
                SELECT
                    SUM(CASE WHEN status = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'loss' THEN 1 ELSE 0 END) as losses
                FROM predictions
                WHERE outcome_date > datetime('now', '-30 days')
            """)
            recent = cursor.fetchone()
            recent_wins = recent[0] or 0
            recent_losses = recent[1] or 0
            recent_total = recent_wins + recent_losses
            recent_win_rate = (recent_wins / recent_total * 100) if recent_total > 0 else 0

            return {
                'total_predictions': sum(status_counts.values()),
                'pending': status_counts.get('pending', 0),
                'wins': wins,
                'losses': losses,
                'expired': status_counts.get('expired', 0),
                'win_rate': win_rate,
                'avg_win_pct': avg_win,
                'avg_loss_pct': avg_loss,
                'profit_factor': profit_factor,
                'by_signal_type': by_signal_type,
                'recent_30d': {
                    'wins': recent_wins,
                    'losses': recent_losses,
                    'win_rate': recent_win_rate
                }
            }

    def manually_resolve(
        self,
        prediction_id: int,
        status: str,
        outcome_price: float,
        notes: Optional[str] = None
    ):
        """Manually resolve a prediction."""
        status_enum = PredictionStatus(status)
        self.update_outcome(prediction_id, status_enum, outcome_price, notes)

    def delete_prediction(self, prediction_id: int):
        """Delete a prediction."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM predictions WHERE id = ?", (prediction_id,))
