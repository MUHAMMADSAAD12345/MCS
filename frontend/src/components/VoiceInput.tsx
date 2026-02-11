import { Mic, MicOff, Volume2 } from 'lucide-react';

interface Props {
  isListening: boolean;
  isSpeaking?: boolean;
  onStart: () => void;
  onStop: () => void;
  onStopSpeaking?: () => void;
}

export function VoiceInput({ isListening, isSpeaking, onStart, onStop, onStopSpeaking }: Props) {
  return (
    <div className="flex gap-1">
      {/* Stop TTS button — only when speaking */}
      {isSpeaking && onStopSpeaking && (
        <button
          onClick={onStopSpeaking}
          className="p-2 rounded-lg bg-purple-600 text-white animate-pulse shadow-lg shadow-purple-600/30 transition-all"
          title="Stop speaking"
        >
          <Volume2 size={18} />
        </button>
      )}
      <button
        onClick={isListening ? onStop : onStart}
        className={`p-2 rounded-lg transition-all ${
          isListening
            ? 'bg-red-600 text-white animate-pulse shadow-lg shadow-red-600/30'
            : 'bg-gray-700 text-gray-400 hover:bg-gray-600 hover:text-gray-200'
        }`}
        title={isListening ? 'Stop listening' : 'Voice input'}
      >
        {isListening ? <MicOff size={18} /> : <Mic size={18} />}
      </button>
    </div>
  );
}
