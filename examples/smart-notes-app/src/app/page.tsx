"use client";

import { useState, useEffect } from 'react';
import { Note, NotesManager, SmartSuggestions } from '../backend/generated/notes_backend';
import NoteCard from '../components/NoteCard';
import NoteEditor from '../components/NoteEditor';

export default function Home() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null); // Add error state
  const [loading, setLoading] = useState(true); // Add loading state

  // Create instances only once
  const [notesManager] = useState(() => new NotesManager());
  const [smartSuggestions] = useState(() => new SmartSuggestions());

  const loadNotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchedNotes = await notesManager.get_notes();
      setNotes(fetchedNotes);
    } catch (e) {
      console.error("Error loading notes:", e);
      setError(`Failed to load notes: ${e instanceof Error ? e.message : String(e)}`);
      setNotes([]);
    } finally {
      setLoading(false);
    }
  };

  // Use useEffect with empty dependency array to load notes once on component mount
  useEffect(() => {
    loadNotes();
  }, []);  // Keep empty dependency array to avoid re-fetching

  async function handleSearch() {
    if (searchQuery.trim()) {
      try {
        setLoading(true);
        setError(null);
        const results = await notesManager.search_notes(searchQuery);
        setNotes(results);
      } catch (e) {
        console.error("Search error:", e);
        setError(`Search failed: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setLoading(false);
      }
    } else {
      loadNotes();
    }
  }

  async function handleNoteSelect(note: Note) {
    setSelectedNote(note);
    setIsEditing(false);
  }

  async function handleCreateNote() {
    setSelectedNote(null);
    setIsEditing(true);
  }

  async function handleSaveNote(title: string, content: string, tags: string[]) {
    try {
      setLoading(true);
      setError(null);

      if (selectedNote) {
        await notesManager.update_note(selectedNote.id, title, content, tags);
      } else {
        await notesManager.add_note(title, content, tags);
      }

      setIsEditing(false);
      await loadNotes();
    } catch (e) {
      console.error("Save error:", e);
      setError(`Failed to save note: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteNote(noteId: string) {
    try {
      setLoading(true);
      setError(null);
      await notesManager.delete_note(noteId);
      setSelectedNote(null);
      await loadNotes();
    } catch (e) {
      console.error("Delete error:", e);
      setError(`Failed to delete note: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  // Display error banner if error exists
  const errorBanner = error ? (
    <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
      <p className="font-bold">Error</p>
      <p>{error}</p>
    </div>
  ) : null;

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto p-4">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-indigo-700">Smart Notes</h1>
          <div className="flex space-x-2">
            <input
              type="text"
              placeholder="Search notes..."
              className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
              onClick={handleSearch}
              disabled={loading}
            >
              {loading ? "..." : "Search"}
            </button>
          </div>
        </div>

        {/* Display error if present */}
        {errorBanner}

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-4 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">Your Notes</h2>
              <button
                className="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700 transition"
                onClick={handleCreateNote}
                disabled={loading}
              >
                + New Note
              </button>
            </div>

            <div className="space-y-3 max-h-[70vh] overflow-y-auto">
              {loading ? (
                <div className="text-center py-8">
                  <p>Loading...</p>
                </div>
              ) : notes.length > 0 ? (
                notes.map(note => (
                  <div
                    key={note.id}
                    onClick={() => handleNoteSelect(note)}
                    className={`p-3 border rounded-lg cursor-pointer hover:shadow-md transition ${
                      selectedNote?.id === note.id ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'
                    }`}
                  >
                    <h3 className="font-medium">{note.title}</h3>
                    <p className="text-sm text-gray-600 truncate">{note.content}</p>
                    <div className="flex flex-wrap mt-2">
                      {note.tags?.map(tag => (
                        <span key={tag} className="text-xs bg-gray-200 px-2 py-1 rounded-full mr-1 mb-1">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No notes found. Create your first note!
                </div>
              )}
            </div>
          </div>

          <div className="col-span-12 md:col-span-8">
            {isEditing ? (
              <NoteEditor
                note={selectedNote}
                onSave={handleSaveNote}
                onCancel={() => setIsEditing(false)}
                smartSuggestions={smartSuggestions}
                isLoading={loading}
              />
            ) : selectedNote ? (
              <NoteCard
                note={selectedNote}
                onEdit={() => setIsEditing(true)}
                onDelete={() => handleDeleteNote(selectedNote.id)}
                isLoading={loading}
              />
            ) : (
              <div className="h-[70vh] flex items-center justify-center border rounded-lg bg-white p-6">
                <div className="text-center text-gray-500">
                  <h2 className="text-xl font-semibold mb-2">Select a note or create a new one</h2>
                  <p>Your notes will appear here</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}