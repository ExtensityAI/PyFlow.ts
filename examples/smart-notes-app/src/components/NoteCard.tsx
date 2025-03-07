// frontend/components/NoteCard.tsx
import { Note } from '../backend/generated/notes_backend';
import { format } from 'date-fns';

interface NoteCardProps {
  note: Note;
  onEdit: () => void;
  onDelete: () => void;
  isLoading?: boolean;
}

export default function NoteCard({ note, onEdit, onDelete, isLoading = false }: NoteCardProps) {
  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy h:mm a');
    } catch {
      return dateString;
    }
  };

  return (
    <div className="border rounded-lg bg-white p-6 shadow-sm h-[70vh] flex flex-col">
      <div className="flex justify-between items-start mb-4">
        <h2 className="text-2xl font-bold text-gray-800">{note.title}</h2>
        <div className="flex space-x-2">
          <button
            onClick={onEdit}
            className="bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700 transition"
            disabled={isLoading}
          >
            Edit
          </button>
          <button
            onClick={onDelete}
            className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 transition"
            disabled={isLoading}
          >
            Delete
          </button>
        </div>
      </div>

      <div className="flex items-center text-sm text-gray-500 mb-4">
        <span>Created: {formatDate(note.created_at)}</span>
        <span className="mx-2">•</span>
        <span>Updated: {formatDate(note.updated_at)}</span>
      </div>

      <div className="flex flex-wrap mb-4">
        {note.tags.map(tag => (
          <span key={tag} className="bg-indigo-100 text-indigo-800 px-2 py-1 rounded-full text-sm mr-2 mb-2">
            #{tag}
          </span>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto prose max-w-none">
        <p className="whitespace-pre-wrap">{note.content}</p>
      </div>
    </div>
  );
}