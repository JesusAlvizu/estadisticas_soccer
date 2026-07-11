"""Machine Learning models for predictions."""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib
from pathlib import Path
from loguru import logger


class MLModelTrainer:
    """Train and manage ML models for predictions."""

    def __init__(self, model_dir: str = "models"):
        """Initialize trainer.
        
        Args:
            model_dir: Directory to save models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.models = {
            'logistic_regression': LogisticRegression(max_iter=1000),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'xgboost': XGBClassifier(n_estimators=100, random_state=42, n_jobs=-1),
            'lightgbm': LGBMClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        }
        
        self.scaler = StandardScaler()
        self.trained_models = {}
        self.metrics = {}
        
        logger.info(f"ML Trainer initialized with model directory: {model_dir}")

    async def prepare_data(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> tuple:
        """Prepare data for training.
        
        Args:
            X: Features
            y: Target
            test_size: Test set size ratio
            random_state: Random state for reproducibility
        """
        logger.info(f"Preparing data: {X.shape[0]} samples, {X.shape[1]} features")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info(f"Data prepared: Train={X_train.shape}, Test={X_test.shape}")
        
        return X_train_scaled, X_test_scaled, y_train, y_test

    async def train_model(
        self,
        model_name: str,
        X_train: np.ndarray,
        y_train: pd.Series,
        X_test: np.ndarray,
        y_test: pd.Series,
    ) -> dict:
        """Train a single model.
        
        Args:
            model_name: Name of model to train
            X_train: Training features
            y_train: Training target
            X_test: Test features
            y_test: Test target
        """
        if model_name not in self.models:
            logger.error(f"Unknown model: {model_name}")
            raise ValueError(f"Unknown model: {model_name}")
        
        logger.info(f"Training model: {model_name}")
        
        model = self.models[model_name]
        model.fit(X_train, y_train)
        
        # Make predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
        }
        
        self.trained_models[model_name] = model
        self.metrics[model_name] = metrics
        
        logger.info(f"Model trained: {model_name}")
        logger.info(f"Metrics: {metrics}")
        
        return metrics

    async def train_all_models(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> dict:
        """Train all models.
        
        Args:
            X: Features
            y: Target
        """
        logger.info("Starting training of all models")
        
        X_train, X_test, y_train, y_test = await self.prepare_data(X, y)
        
        all_metrics = {}
        for model_name in self.models.keys():
            try:
                metrics = await self.train_model(
                    model_name, X_train, y_train, X_test, y_test
                )
                all_metrics[model_name] = metrics
            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
        
        # Train voting ensemble
        logger.info("Training Voting Ensemble")
        ensemble = VotingClassifier(
            estimators=[
                ('lr', self.trained_models.get('logistic_regression')),
                ('rf', self.trained_models.get('random_forest')),
                ('xgb', self.trained_models.get('xgboost')),
                ('lgb', self.trained_models.get('lightgbm')),
            ],
            voting='soft',
        )
        
        ensemble.fit(X_train, y_train)
        y_pred = ensemble.predict(X_test)
        y_pred_proba = ensemble.predict_proba(X_test)[:, 1]
        
        ensemble_metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
        }
        
        self.trained_models['voting_ensemble'] = ensemble
        self.metrics['voting_ensemble'] = ensemble_metrics
        all_metrics['voting_ensemble'] = ensemble_metrics
        
        logger.info("All models trained successfully")
        return all_metrics

    async def save_models(self) -> dict:
        """Save trained models to disk."""
        logger.info("Saving models to disk")
        
        saved_models = {}
        for model_name, model in self.trained_models.items():
            model_path = self.model_dir / f"{model_name}.pkl"
            joblib.dump(model, model_path)
            saved_models[model_name] = str(model_path)
            logger.info(f"Saved {model_name} to {model_path}")
        
        # Save scaler
        scaler_path = self.model_dir / "scaler.pkl"
        joblib.dump(self.scaler, scaler_path)
        
        return saved_models

    async def load_models(self) -> bool:
        """Load trained models from disk."""
        logger.info("Loading models from disk")
        
        all_loaded = True
        for model_name in self.models.keys():
            model_path = self.model_dir / f"{model_name}.pkl"
            if model_path.exists():
                self.trained_models[model_name] = joblib.load(model_path)
                logger.info(f"Loaded {model_name}")
            else:
                logger.warning(f"Model not found: {model_name}")
                all_loaded = False
        
        # Load scaler
        scaler_path = self.model_dir / "scaler.pkl"
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
        
        return all_loaded

    async def predict(self, X: pd.DataFrame, model_name: str = 'voting_ensemble') -> tuple:
        """Make predictions.
        
        Args:
            X: Features
            model_name: Model to use for prediction
        """
        if model_name not in self.trained_models:
            logger.error(f"Model not trained: {model_name}")
            raise ValueError(f"Model not trained: {model_name}")
        
        X_scaled = self.scaler.transform(X)
        model = self.trained_models[model_name]
        
        y_pred = model.predict(X_scaled)
        y_pred_proba = model.predict_proba(X_scaled)
        
        return y_pred, y_pred_proba

    async def get_best_model(self) -> tuple[str, dict]:
        """Get best model based on F1 score."""
        best_model = max(
            self.metrics.items(),
            key=lambda x: x[1].get('f1', 0)
        )
        return best_model
