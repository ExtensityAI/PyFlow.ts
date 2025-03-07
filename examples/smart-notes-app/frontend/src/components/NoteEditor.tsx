// frontend/components/NoteEditor.tsx
import { useState, useEffect } from 'react';
import { Note, SmartSuggestions } from '../backend/generated/notes_backend';

interface NoteEditorProps {
  note: Note | null;
  onSave: (title: string, content: string, tags: string[]) => void;
  onCancel: () => void;
  smartSuggestions: SmartSuggestions;
  isLoading?: boolean;
}

export default function NoteEditor({ note, onSave, onCancel, smartSuggestions, isLoading = false }: NoteEditorProps) {
  const [title, setTitle] = useState(note?.title || '');
  const [content, setContent] = useState(note?.content || '');
  const [tags, setTags] = useState<string[]>(note?.tags || []);
  const [tagInput, setTagInput] = useState('');
  const [suggestedTags, setSuggestedTags] = useState<string[]>([]);
  const [showContinuationSuggestion, setShowContinuationSuggestion] = useState(false);
  const [continuationSuggestion, setContinuationSuggestion] = useState('');

  // Get tag suggestions when content changes
  useEffect(() => {
    const getSuggestions = async () => {
      if (content.trim().length > 10) {
        const suggestions = await smartSuggestions.suggest_tags(content);
        setSuggestedTags(suggestions.filter(tag => !tags.includes(tag)));

        // Get continuation suggestion if content ends with a period and is long enough
        if (content.trim().endsWith('.') && content.trim().length > 50) {
          const continuation = await smartSuggestions.suggest_continuation(content);
          setContinuationSuggestion(continuation);
          setShowContinuationSuggestion(true);
        } else {
          setShowContinuationSuggestion(false);
        }
      } else {
        setSuggestedTags([]);
        setShowContinuationSuggestion(false);
      }
    };

    const delayDebounce = setTimeout(getSuggestions, 1000);
    return () => clearTimeout(delayDebounce);
  }, [content, smartSuggestions, tags]);

  const handleAddTag = (tag: string) => {
    if (tag.trim() && !tags.includes(tag.trim())) {
      setTags([...tags, tag.trim()]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const handleAddSuggestedTag = (tag: string) => {
    if (!tags.includes(tag)) {
      setTags([...tags, tag]);
      setSuggestedTags(suggestedTags.filter(t => t !== tag));
    }
  };

  const handleApplyContinuation = () => {
    setContent(content + continuationSuggestion);
    setShowContinuationSuggestion(false);
  };

  const handleSubmit = () => {
    if (title.trim() && content.trim()) {
      onSave(title, content, tags);
    }
  };

  return (
    <div className="border rounded-lg bg-white p-6 shadow-sm h-[70vh] flex flex-col">
      <input
        type="text"
        placeholder="Note title"
        className="text-2xl font-bold border-b border-gray-200 pb-2 mb-4 focus:outline-none focus:border-indigo-500"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        disabled={isLoading}
      />

      <div className="relative flex-1 mb-4">
        <textarea
          placeholder="Write your note here..."
          className="w-full h-full p-3 border rounded resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={isLoading}
        />

        {showContinuationSuggestion && (
          <div className="absolute bottom-3 right-3 bg-indigo-100 p-3 rounded-lg shadow-md max-w-md">
            <p className="text-gray-700 mb-2">
              <span className="font-semibold">Suggestion:</span>
              <span className="italic">{continuationSuggestion}</span>
            </p>
            <div className="flex justify-end">
              <button
                onClick={handleApplyContinuation}
                className="bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700 text-sm"
                disabled={isLoading}
              >
                Use Suggestion
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mb-4">
        <div className="text-sm font-medium mb-2">Tags</div>
        <div className="flex flex-wrap gap-2 mb-2">
          {tags.map(tag => (
            <span key={tag} className="bg-indigo-100 text-indigo-800 px-2 py-1 rounded-full flex items-center">
              #{tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                className="ml-1 text-indigo-500 hover:text-indigo-700"
                disabled={isLoading}
              >
                &times;
              </button>
            </span>
          ))}

          <div className="flex items-center">
            <input
              type="text"
              placeholder="Add tag..."
              className="px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddTag(tagInput)}
              disabled={isLoading}
            />
            <button
              onClick={() => handleAddTag(tagInput)}
              className="ml-1 bg-gray-200 px-2 py-1 rounded text-sm hover:bg-gray-300"
              disabled={isLoading}
            >
              Add
            </button>
          </div>
        </div>

        {suggestedTags.length > 0 && (
          <div>
            <div className="text-sm text-gray-600 mb-1">Suggested tags:</div>
            <div className="flex flex-wrap gap-2">
              {suggestedTags.map(tag => (
                <button
                  key={tag}
                  onClick={() => handleAddSuggestedTag(tag)}
                  className="bg-gray-100 hover:bg-indigo-100 text-gray-700 px-2 py-1 rounded-full text-sm transition"
                  disabled={isLoading}
                >
                  #{tag}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-end space-x-3">
        <button
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100 transition"
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition"
          disabled={isLoading}
        >
          Save Note
        </button>
      </div>
    </div>
  );
}