"""
User Profile Service

Responsible for aggregating raw database signals (ratings, chats, insights)
into a compressed, context-rich "User Profile Summary" for the LLM.

This solves the "Amnesia" problem by ensuring the bot always knows
the user's long-term preferences, even in a new chat session.
"""

from typing import List, Dict, Optional
from app.db.database import Database

class UserProfileService:
    def __init__(self, db: Database):
        self.db = db

    def get_profile_summary(self, user_id: int) -> str:
        """
        Generate a concise, bulleted summary of the user's profile.
        Designed to be injected into LLM System Prompts.
        """
        if not user_id:
            return "User Profile: Anonymous / New User"

        user = self.db.get_user(user_id)
        if not user:
            return "User Profile: Unknown"

        # 1. Basic Info
        name = user.get("display_name", "Friend")
        personality = user.get("personality", "friendly")
        
        # 2. Insights (Long-term generic preferences)
        insights = self.db.get_user_insights(user_id)
        formatted_insights = []
        for i in insights:
            # Insights are often "User likes X". We just list them.
            formatted_insights.append(f"- {i['content']}")
            
        # 3. Reading History & Ratings (The most important part)
        # We need a query for this. Assuming db.get_user_books() exists or similar.
        # Since it might not, we'll try to fetch recent interactions or rely on insights.
        # For this v1, let's look at the 'interactions' table via a new DB method if possible,
        # or just fallback to insights.
        
        # Let's assume we can get recent high-rated books
        # (We will add this method to database.py next)
        top_reads = self._get_top_reads(user_id)
        
        summary_lines = [
            f"USER PROFILE ({name}):",
            f"- Preferred Assistant Persona: {personality.title()}",
        ]
        
        if formatted_insights:
            summary_lines.append("KNOWN PREFERENCES:")
            summary_lines.extend(formatted_insights[:5]) # Limit to 5 for space
            
        if top_reads:
            summary_lines.append("HIGHLY RATED BOOKS:")
            summary_lines.extend(top_reads)
            
        # 4. Recent Mood (derived from last few chats)
        recent_mood = self._detect_recent_mood(user_id)
        if recent_mood:
             summary_lines.append(f"CURRENT MOOD: {recent_mood}")

        return "\n".join(summary_lines)

    def _get_top_reads(self, user_id: int) -> List[str]:
        """Fetch top rated/read books for the profile."""
        try:
            return self.db.get_user_read_history(user_id, limit=3)
        except Exception as e:
            print(f"Profile error: {e}")
            return []

    def _detect_recent_mood(self, user_id: int) -> Optional[str]:
        """Technically this would analyze recent chat entries."""
        # For now, placeholder.
        return None

def get_profile_service(db: Database) -> UserProfileService:
    return UserProfileService(db)
