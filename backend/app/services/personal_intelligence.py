"""
Personal Intelligence Service

Loads the trained PyTorch model (personal_intelligence_v2.pth) and provides:
- predict_scores(book_ids, mood): Deterministic ranking scores
- predict_strategy(mood): Strategy selection (comfort, challenge, etc.)

This is the AUTHORITATIVE decision-maker. The LLM does NOT override this.
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Try to import torch, but don't fail if it's not installed
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[PersonalIntelligence] PyTorch not installed. Using fallback logic.")


# ============================================================
# MODEL DEFINITION (Must match the training architecture)
# ============================================================
if TORCH_AVAILABLE:
    class PersonalDecisionModel(nn.Module):
        """
        Multi-task model for book scoring and strategy prediction.
        Architecture must match the trained model exactly.
        """
        def __init__(self, num_books: int = 1000, num_moods: int = 4, 
                     num_strategies: int = 4, emb_dim: int = 64):
            super(PersonalDecisionModel, self).__init__()
            
            # Single learned user vector (not per-user embeddings)
            self.user_vector = nn.Parameter(torch.randn(emb_dim))
            
            # Book embeddings
            self.book_emb = nn.Embedding(num_books, emb_dim)
            
            # Mood embeddings
            self.mood_emb = nn.Embedding(num_moods, emb_dim // 2)
            
            # Ranking Head (User + Book -> Score)
            self.ranking_mlp = nn.Sequential(
                nn.Linear(emb_dim * 2, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 1)
            )
            
            # Strategy Head (User + Mood -> Strategy)
            self.strategy_mlp = nn.Sequential(
                nn.Linear(emb_dim + (emb_dim // 2), 64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, num_strategies)
            )

        def forward(self, book_idx: torch.Tensor, mood_idx: torch.Tensor):
            # Expand user vector for batch
            batch_size = book_idx.size(0)
            u_emb = self.user_vector.unsqueeze(0).expand(batch_size, -1)
            
            b_emb = self.book_emb(book_idx)
            m_emb = self.mood_emb(mood_idx)
            
            # Task 1: Score books
            rank_input = torch.cat([u_emb, b_emb], dim=1)
            scores = self.ranking_mlp(rank_input)
            
            # Task 2: Decide strategy
            strat_input = torch.cat([u_emb, m_emb], dim=1)
            strategy_logits = self.strategy_mlp(strat_input)
            
            return scores, strategy_logits


# ============================================================
# SERVICE CLASS
# ============================================================
class PersonalIntelligenceService:
    """
    Loads and runs inference on the trained Personal Intelligence Model.
    """
    
    MOOD_MAP = {
        "neutral": 0,
        "calm": 0,
        "stressed": 1,
        "anxious": 1,
        "curious": 2,
        "excited": 2,
        "bored": 3
    }
    
    STRATEGY_MAP = {
        0: "standard",
        1: "comfort",
        2: "challenge",
        3: "explore"
    }
    
    def __init__(self, model_path: str = None):
        self.model = None
        self.device = "cpu"
        self.metadata = {}
        self.book_to_idx = {}
        
        if model_path is None:
            # Default path relative to backend folder
            model_path = Path(__file__).parent.parent.parent / "personal_intelligence_v2.pth"
        
        self._load_model(model_path)
    
    def _load_model(self, model_path: str):
        """Load the trained PyTorch model."""
        if not TORCH_AVAILABLE:
            print("[PersonalIntelligence] PyTorch not available. Running in fallback mode.")
            return
        
        model_path = Path(model_path)
        if not model_path.exists():
            print(f"[PersonalIntelligence] Model not found at: {model_path}")
            return
        
        try:
            # Load the checkpoint
            checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
            
            # Check if it's a full checkpoint or just state_dict
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
                self.metadata = checkpoint.get("metadata", {})
                self.book_to_idx = checkpoint.get("book_map", {})
            else:
                state_dict = checkpoint
            
            # Infer model dimensions from state_dict
            num_books = state_dict.get("book_emb.weight", torch.zeros(1000, 64)).size(0)
            num_moods = state_dict.get("mood_emb.weight", torch.zeros(4, 32)).size(0)
            emb_dim = state_dict.get("user_vector", torch.zeros(64)).size(0)
            
            # Initialize model
            self.model = PersonalDecisionModel(
                num_books=num_books,
                num_moods=num_moods,
                num_strategies=4,
                emb_dim=emb_dim
            )
            
            # Load weights
            self.model.load_state_dict(state_dict, strict=False)
            self.model.eval()
            
            print(f"[PersonalIntelligence] Model loaded! Books: {num_books}, Dim: {emb_dim}")
            
        except Exception as e:
            print(f"[PersonalIntelligence] Failed to load model: {e}")
            self.model = None
    
    def predict_scores(self, book_ids: List[str], mood: str = "neutral") -> List[Tuple[str, float]]:
        """
        Predict relevance scores for a list of books given the current mood.
        Returns list of (book_id, score) tuples sorted by score descending.
        """
        if self.model is None:
            # Fallback: return books in original order with dummy scores
            return [(bid, 3.0 + i * 0.1) for i, bid in enumerate(book_ids)]
        
        mood_idx = self.MOOD_MAP.get(mood.lower(), 0)
        
        results = []
        for book_id in book_ids:
            # Map book_id to index (fallback to hash if not in map)
            if book_id in self.book_to_idx:
                b_idx = self.book_to_idx[book_id]
            else:
                b_idx = hash(book_id) % self.model.book_emb.num_embeddings
            
            with torch.no_grad():
                b_tensor = torch.tensor([b_idx], dtype=torch.long)
                m_tensor = torch.tensor([mood_idx], dtype=torch.long)
                
                score, _ = self.model(b_tensor, m_tensor)
                results.append((book_id, float(score.squeeze().item())))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def predict_strategy(self, mood: str = "neutral") -> str:
        """
        Predict the best interaction strategy based on mood.
        Returns one of: standard, comfort, challenge, explore
        """
        if self.model is None:
            # Fallback logic
            mood_lower = mood.lower()
            if mood_lower in ["stressed", "anxious", "sad"]:
                return "comfort"
            elif mood_lower in ["curious", "excited"]:
                return "challenge"
            elif mood_lower in ["bored"]:
                return "explore"
            return "standard"
        
        mood_idx = self.MOOD_MAP.get(mood.lower(), 0)
        
        with torch.no_grad():
            # Use a dummy book index for strategy prediction
            b_tensor = torch.tensor([0], dtype=torch.long)
            m_tensor = torch.tensor([mood_idx], dtype=torch.long)
            
            _, strategy_logits = self.model(b_tensor, m_tensor)
            strategy_idx = int(torch.argmax(strategy_logits, dim=1).item())
            
        return self.STRATEGY_MAP.get(strategy_idx, "standard")


# ============================================================
# SINGLETON
# ============================================================
_service_instance: Optional[PersonalIntelligenceService] = None

def get_personal_intelligence_service() -> PersonalIntelligenceService:
    """Get or create the PersonalIntelligenceService singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = PersonalIntelligenceService()
    return _service_instance
