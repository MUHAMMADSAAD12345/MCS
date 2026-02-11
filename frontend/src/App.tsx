import { useChatStore } from './stores/chatStore';
import { AuthScreen } from './components/AuthScreen';
import { ChatWindow } from './components/ChatWindow';

export default function App() {
  const { auth } = useChatStore();

  if (!auth.token) {
    return <AuthScreen />;
  }

  return <ChatWindow />;
}
