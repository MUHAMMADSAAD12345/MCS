import { useState, useRef, useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';
import { Upload, FileText, Trash2, X, Loader2 } from 'lucide-react';
import type { UploadedDocument } from '../types';

export function DocumentSidebar() {
  const { auth, documents, setDocuments, addDocument, removeDocument } = useChatStore();
  const [isOpen, setIsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch documents on open
  const fetchDocs = useCallback(async () => {
    if (!auth.token) return;
    try {
      const res = await fetch('/api/documents/list', {
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch {}
  }, [auth.token]);

  const handleOpen = () => {
    setIsOpen(true);
    fetchDocs();
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !auth.token) return;

    setUploading(true);
    const form = new FormData();
    form.append('file', file);

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: form,
      });
      if (res.ok) {
        const data = await res.json();
        addDocument(data.document);
        await fetchDocs();
      } else {
        console.error('Upload failed:', await res.text());
      }
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (doc: UploadedDocument) => {
    if (!auth.token) return;
    try {
      const res = await fetch(`/api/documents/${doc.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (res.ok) removeDocument(doc.id);
    } catch {}
  };

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={handleOpen}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300 transition-colors border border-gray-700"
      >
        <FileText size={14} />
        Docs ({documents.length})
      </button>

      {/* Sidebar overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setIsOpen(false)} />
          <div className="relative w-80 bg-gray-900 border-l border-gray-700 p-4 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">Knowledge Base</h3>
              <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white">
                <X size={18} />
              </button>
            </div>

            {/* Upload */}
            <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-gray-800/50 transition-colors mb-4">
              {uploading ? (
                <Loader2 size={16} className="animate-spin text-blue-400" />
              ) : (
                <Upload size={16} className="text-gray-400" />
              )}
              <span className="text-xs text-gray-400">
                {uploading ? 'Uploading...' : 'Upload PDF, DOCX, TXT, CSV, MD'}
              </span>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.csv,.md"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>

            {/* Document list */}
            <div className="flex-1 overflow-y-auto space-y-2">
              {documents.length === 0 ? (
                <p className="text-xs text-gray-500 text-center mt-8">
                  No documents uploaded yet.
                </p>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg border border-gray-700"
                  >
                    <FileText size={16} className="text-blue-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-200 truncate">
                        {doc.filename}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        {doc.chunk_count} chunks · {doc.file_type}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDelete(doc)}
                      className="text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
