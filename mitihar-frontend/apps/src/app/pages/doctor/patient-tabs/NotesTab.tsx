import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { doctorApi } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import { Plus, StickyNote, Send, Loader2 } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';

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
    general:  'bg-muted text-secondary-foreground',
    dietary:  'bg-brand-100 text-brand-700',
    medical:  'bg-blue-50 text-blue-600',
    progress: 'bg-amber-50 text-amber-700',
  };

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Clinical Notes</h2>
          <p className="text-sm text-muted-foreground">Notes for {patientName} — visible only to you</p>
        </div>
        <Button variant="primary" size="md" onClick={() => setAdding(!adding)}>
          <Plus size={14} />
          Add Note
        </Button>
      </div>

      {/* Add note form */}
      {adding && (
        <Card className="bg-brand-50 border-brand-100 p-4 mb-4">
          {/* Note type selector */}
          <div className="flex gap-2 mb-3 flex-wrap">
            {NOTE_TYPES.map(t => (
              <button
                key={t}
                onClick={() => setNoteType(t)}
                className={`h-7 px-3 rounded-full text-xs font-medium capitalize transition-colors ${
                  noteType === t
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card border border-border text-secondary-foreground hover:border-primary'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <textarea
            value={newNote}
            onChange={e => setNewNote(e.target.value)}
            placeholder="Add a clinical note about this patient…"
            rows={3}
            className="w-full resize-none bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          />
          <div className="flex items-center justify-end gap-2 mt-2">
            <Button variant="outline" size="sm" onClick={() => { setAdding(false); setNewNote(''); setNoteType('general'); }}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleAdd} disabled={!newNote.trim() || addMutation.isPending}>
              {addMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
              Save Note
            </Button>
          </div>
        </Card>
      )}

      {/* Notes list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={20} className="animate-spin text-primary" />
        </div>
      ) : notes.length === 0 ? (
        <Card className="py-14 text-center">
          <StickyNote size={20} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-base font-medium text-secondary-foreground">No notes yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Add clinical notes to keep track of important observations.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {notes.map(note => (
            <Card key={note.id} className="p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium capitalize ${noteTypeBadge[note.note_type as NoteType] ?? noteTypeBadge.general}`}
                >
                  {note.note_type}
                </span>
                <p className="text-xs text-muted-foreground font-mono">{formatDate(note.created_at)}</p>
              </div>
              <p className="text-sm text-secondary-foreground leading-relaxed">{note.content}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
