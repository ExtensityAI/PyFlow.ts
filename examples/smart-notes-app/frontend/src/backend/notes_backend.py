# notes_backend.py
from pyflow import extensity
from typing import List, Dict, Optional
import datetime
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer

# Simple in-memory database for demo
notes_db = {}
embeddings_db = {}
model = SentenceTransformer('all-MiniLM-L6-v2')

@extensity
class Note:
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    tags: List[str]

@extensity
class NotesManager:
    def __init__(self):
        # Initialize with some example data if empty
        if not notes_db:
            self.add_note("Welcome to SmartNotes", "This is your first note. Try adding more!", ["welcome"])

    def add_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Note:
        now = datetime.datetime.now().isoformat()
        note_id = str(uuid.uuid4())

        note = {
            "id": note_id,
            "title": title,
            "content": content,
            "created_at": now,
            "updated_at": now,
            "tags": tags or []
        }

        notes_db[note_id] = note
        # Store embedding for semantic search
        embeddings_db[note_id] = model.encode(content)

        return note

    def get_notes(self) -> List[Note]:
        return list(notes_db.values())

    def get_note(self, note_id: str) -> Optional[Note]:
        return notes_db.get(note_id)

    def update_note(self, note_id: str, title: Optional[str] = None,
                   content: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[Note]:
        if note_id not in notes_db:
            return None

        note = notes_db[note_id]

        if title:
            note["title"] = title
        if content:
            note["content"] = content
            # Update embedding
            embeddings_db[note_id] = model.encode(content)
        if tags:
            note["tags"] = tags

        note["updated_at"] = datetime.datetime.now().isoformat()
        return note

    def delete_note(self, note_id: str) -> bool:
        if note_id in notes_db:
            del notes_db[note_id]
            if note_id in embeddings_db:
                del embeddings_db[note_id]
            return True
        return False

    def search_notes(self, query: str) -> List[Note]:
        query_embedding = model.encode(query)

        # Calculate similarity scores
        scores = {}
        for note_id, embedding in embeddings_db.items():
            similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
            scores[note_id] = similarity

        # Sort by similarity score
        sorted_notes = sorted([(notes_db[note_id], score) for note_id, score in scores.items()],
                             key=lambda x: x[1], reverse=True)

        # Return just the notes (not the scores)
        return [note for note, _ in sorted_notes]

@extensity
class SmartSuggestions:
    def suggest_tags(self, content: str) -> List[str]:
        # In a real app, this would use a more sophisticated ML model
        # For demo purposes, we'll use a simple keyword-based approach
        common_topics = {
            "work": ["meeting", "project", "deadline", "task", "client", "report"],
            "personal": ["family", "friend", "vacation", "weekend", "birthday"],
            "ideas": ["idea", "thought", "concept", "innovation", "creative"],
            "todo": ["todo", "task", "remember", "don't forget", "reminder"]
        }

        content_lower = content.lower()
        suggested_tags = []

        for tag, keywords in common_topics.items():
            if any(keyword in content_lower for keyword in keywords):
                suggested_tags.append(tag)

        return suggested_tags

    def suggest_continuation(self, content: str) -> str:
        # In a real app, use an LLM API for completions
        # This is a simplified placeholder
        if "meeting" in content.lower():
            return " I need to prepare the following agenda items..."
        elif "idea" in content.lower():
            return " This concept could be developed further by..."
        elif "todo" in content.lower() or "task" in content.lower():
            return " I should prioritize this and set a deadline of..."
        else:
            return " I should expand on this by adding more details about..."