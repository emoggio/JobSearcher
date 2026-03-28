import { useState, useRef, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profileChat } from "../api";
import { MessageSquare, Send, X, Loader2, User, Bot, Minimize2 } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const INITIAL_MESSAGE: Message = {
  role: "assistant",
  content:
    "Hi! I'm your job search assistant. Tell me what you're looking for — target role, industries, must-haves, deal-breakers. The more you share, the better I can tune your job scoring.",
};

export default function FloatingChat() {
  const qc = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");

  const { mutate: send, isPending: sending } = useMutation({
    mutationFn: async (text: string) => {
      const updated: Message[] = [...messages, { role: "user", content: text }];
      setMessages(updated);
      const { data } = await profileChat(updated);
      return data;
    },
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      if (data.context_updated) {
        qc.invalidateQueries({ queryKey: ["profile"] });
        qc.invalidateQueries({ queryKey: ["jobs"] });
      }
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    },
  });

  function handleSend() {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput("");
    send(text);
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const unread = !open && messages.length > 1 &&
    messages[messages.length - 1].role === "assistant";

  return (
    <>
      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-[4.5rem] right-3 left-3 md:left-auto md:bottom-[4.5rem] md:right-6 md:w-96 h-[min(520px,calc(100dvh-6rem))] bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900 shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center">
                <Bot size={12} className="text-indigo-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Job Search Assistant</p>
                <p className="text-[10px] text-gray-500">Refine your preferences</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-500 hover:text-white transition-colors p-1"
            >
              <Minimize2 size={14} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-auto px-3 py-3 space-y-3">
            {messages.map((msg, i) => {
              const isUser = msg.role === "user";
              return (
                <div key={i} className={`flex gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    isUser ? "bg-indigo-600" : "bg-gray-800 border border-gray-700"
                  }`}>
                    {isUser
                      ? <User size={11} />
                      : <Bot size={11} className="text-indigo-400" />
                    }
                  </div>
                  <div className={`max-w-[80%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                    isUser
                      ? "bg-indigo-600 text-white rounded-tr-sm"
                      : "bg-gray-800 border border-gray-700/50 text-gray-200 rounded-tl-sm"
                  }`}>
                    {msg.content}
                  </div>
                </div>
              );
            })}
            {sending && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0">
                  <Bot size={11} className="text-indigo-400" />
                </div>
                <div className="bg-gray-800 border border-gray-700/50 rounded-xl rounded-tl-sm px-3 py-2">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="shrink-0 px-3 py-3 border-t border-gray-800">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="flex gap-2"
            >
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Tell me what you want…"
                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-xs outline-none focus:border-indigo-500 transition-colors placeholder-gray-600"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="flex items-center justify-center w-8 h-8 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-xl transition-colors shrink-0"
              >
                <Send size={12} />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`fixed bottom-16 right-4 md:bottom-6 md:right-6 w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all z-50 ${
          open
            ? "bg-gray-700 hover:bg-gray-600"
            : "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-900/40"
        }`}
        title="Job search assistant"
      >
        {open ? <X size={18} /> : <MessageSquare size={18} />}
        {unread && !open && (
          <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-gray-950" />
        )}
      </button>
    </>
  );
}
