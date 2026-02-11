import { Download, FileText, FileSpreadsheet, File } from 'lucide-react';

interface Props {
  filename: string;
  downloadUrl: string;
}

function getIcon(filename: string) {
  if (filename.endsWith('.pdf')) return <File size={16} className="text-red-400" />;
  if (filename.endsWith('.docx')) return <FileText size={16} className="text-blue-400" />;
  if (filename.endsWith('.xlsx')) return <FileSpreadsheet size={16} className="text-green-400" />;
  return <File size={16} className="text-gray-400" />;
}

export function DownloadCard({ filename, downloadUrl }: Props) {
  return (
    <a
      href={downloadUrl}
      download
      className="inline-flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg transition-colors mt-2"
    >
      {getIcon(filename)}
      <span className="text-xs text-gray-200 font-medium">{filename}</span>
      <Download size={14} className="text-gray-400" />
    </a>
  );
}
