import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { doctorApi } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import { Plus, StickyNote, Send, Loader2 } from 'lucide-react';

interface NotesTabProps {
  patientId: number;
  patientName: string;
}

const NOTE_TYPES = ['general', 'dietary', 'medical', 'progress'] as const;
type NoteType = typeof NOTE_TYPES[number];

export function NotesTab({ patientId, patientName }: NotesTabProps) {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [noteType, setNoteType] = useState<NoteType>('general');

  const { data: notes = [], isLoading } = useQuery({
    queryKey: qk.patientNotes(patientId),
    queryFn: () => doctorApi.getPatientNotes(patientId),
  });

  const addMutation = useMutation({
    mutationFn: () => doctorApi.addPatientNote(patientId, newNote.trim(), noteType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.patientNotes(patientId) });
      setNewNote('');
      setNoteType('general');
      setAdding(false);
      toast.success('Note added');
    },
    onError: () => toast.error('Failed to save note'),
  });

  const handleAdd = () => {
    if (!newNote.trim()) return;
    addMutation.mutate();
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric',
      });
    } catch {
      return iso;
    }
  };

  const noteTypeBadge: Record<NoteType, string> = {
    general:  'bg-[#F3F4F6] text-[#374151]',
    dietary:  'bg-[#DCFCE7] text-[#15803d]',
    medical:  'bg-[#EFF6FF] text-[#2563EB]',
    progress: 'bg-[#FFFBEB] text-[#B45309]',
  };

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-[#111827]">Clinical Notes</h2>
          <p className="text-sm text-[#6B7280]">Notes for {patientName} — visible only to you</p>
        </div>
        <button
          onClick={() => setAdding(!adding)}
          className="flex items-center gap-2 h-9 px-3 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
        >
          <Plus size={15} />
          Add Note
        </button>
      </div>

      {/* Add note form */}
      {adding && (
        <div className="bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg p-4 mb-4">
          {/* Note type selector */}
          <div className="flex gap-2 mb-3 flex-wrap">
            {NOTE_TYPES.map(t => (
              <button
                key={t}
                onClick={() => setNoteType(t)}
                className={`h-7 px-3 rounded-full text-xs font-medium capitalize transition-colors ${
                  noteType === t
                    ? 'bg-[#1E7C45] text-white'
                    : 'bg-white border border-[#D1D5DB] text-[#374151] hover:border-[#1E7C45]'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <textarea
            value={newNote}
            onChange={e => setNewNote(e.target.value)}
            autoFocus
            placeholder="Add a clinical note about this patient…"
            rows={3}
            className="w-full resize-none bg-white border border-[#D1D5DB] rounded-md px-3 py-2 text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
          />
          <div className="flex items-center justify-end gap-2 mt-2">
            <button
              onClick={() => { setAdding(false); setNewNote(''); setNoteType('general'); }}
              className="h-8 px-3 rounded border border-[#D1D5DB] bg-white text-sm text-[#374151] hover:bg-[#F9FAFB] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!newNote.trim() || addMutation.isPending}
              className="flex items-center gap-1.5 h-8 px-3 rounded bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50"
            >
              {addMutation.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              Save Note
            </button>
          </div>
        </div>
      )}

      {/* Notes list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
        </div>
      ) : notes.length === 0 ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
          <StickyNote size={32} className="text-[#D1D5DB] mx-auto mb-3" />
          <p className="text-base font-medium text-[#374151]">No notes yet</p>
          <p className="text-sm text-[#6B7280] mt-1">
            Add clinical notes to keep track of important observations.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {notes.map(note => (
            <div key={note.id} className="bg-white border border-[#E5E7EB] rounded-lg p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium capitalize ${noteTypeBadge[note.note_type as NoteType] ?? noteTypeBadge.general}`}
                >
                  {note.note_type}
                </span>
                <p className="text-xs text-[#9CA3AF] font-mono">{formatDate(note.created_at)}</p>
              </div>
              <p className="text-sm text-[#374151] leading-relaxed">{note.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
