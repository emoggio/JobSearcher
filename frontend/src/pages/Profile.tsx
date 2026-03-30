import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getProfile, profileChat, generateProfileQuestions, saveProfileAnswers, clearProfileData, getSkillsGap } from "../api";
import {
  MessageSquare, Send, Loader2, RefreshCw, CheckCircle2,
  ChevronDown, ChevronUp, Sparkles, User, Bot, Trash2, BarChart2,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
        isUser ? "bg-indigo-600" : "bg-gray-800 border border-gray-700"
      }`}>
        {isUser ? <User size={13} /> : <Bot size={13} className="text-indigo-400" />}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        isUser
          ? "bg-indigo-600 text-white rounded-tr-sm"
          : "bg-gray-900 border border-gray-800 text-gray-200 rounded-tl-sm"
      }`}>
        {message.content}
      </div>
    </div>
  );
}

export default function Profile() {
  const qc = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your job search assistant. I'm here to help you find the right opportunities — not just any job, but the one you actually want. Tell me what kind of role you're looking for, what's most important to you, and what you want to avoid. The more context you give me, the better I can tailor your job matches and scoring.",
    },
  ]);
  const [input, setInput] = useState("");
  const [showProfile, setShowProfile] = useState(false);
  const [showQA, setShowQA] = useState(false);
  const [qaAnswers, setQaAnswers] = useState<Record<number, string>>({});

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: () => getProfile().then((r) => r.data),
  });

  const { mutate: sendMessage, isPending: sending } = useMutation({
    mutationFn: async (text: string) => {
      const newMessages: Message[] = [...messages, { role: "user", content: text }];
      setMessages(newMessages);
      const { data } = await profileChat(newMessages);
      return data;
    },
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      if (data.context_updated) {
        qc.invalidateQueries({ queryKey: ["profile"] });
      }
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    },
  });

  const { mutate: generateQuestions, isPending: generatingQs } = useMutation({
    mutationFn: () => generateProfileQuestions(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });

  const { mutate: clearProfile, isPending: clearing } = useMutation({
    mutationFn: () => clearProfileData(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      setMessages([{
        role: "assistant",
        content: "Your search profile has been cleared. Let's start fresh — tell me what you're looking for in your next role.",
      }]);
      setQaAnswers({});
    },
  });

  const { mutate: saveAnswers, isPending: savingAnswers } = useMutation({
    mutationFn: () => {
      const questions: string[] = profile?.questions || [];
      const qa_pairs = questions
        .map((q: string, i: number) => ({ question: q, answer: qaAnswers[i] || "" }))
        .filter((p) => p.answer.trim());
      return saveProfileAnswers(qa_pairs);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      setShowQA(false);
    },
  });

  const [skillsGapResults, setSkillsGapResults] = useState<any[] | null>(null);
  const [skillsGapMsg, setSkillsGapMsg] = useState<string | null>(null);
  const { mutate: analyseGap, isPending: analysingGap } = useMutation({
    mutationFn: () => getSkillsGap(),
    onSuccess: (res) => {
      const data = res.data;
      if (data?.no_jobs) {
        setSkillsGapMsg("Run a search and score jobs first");
        setSkillsGapResults(null);
      } else if (!data?.gaps || data.gaps.length === 0) {
        setSkillsGapMsg("Your CV covers the key skills well");
        setSkillsGapResults(null);
      } else {
        setSkillsGapResults(data.gaps);
        setSkillsGapMsg(null);
      }
    },
    onError: () => {
      setSkillsGapMsg("Failed to fetch skills gap. Please try again.");
      setSkillsGapResults(null);
    },
  });

  function handleSend() {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput("");
    sendMessage(text);
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const questions: string[] = profile?.questions || [];
  const savedContext = profile?.search_context || "";

  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header */}
      <div className="shrink-0 px-4 md:px-6 py-4 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <MessageSquare size={18} className="text-indigo-400" />
              Job Search Chat
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Talk to Claude to refine your search and improve job matching
            </p>
          </div>
          <div className="flex items-center gap-2">
            {savedContext && (
              <button
                onClick={() => clearProfile()}
                disabled={clearing}
                title="Clear all saved preferences and start fresh"
                className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 bg-red-900/20 border border-red-800/30 px-3 py-1.5 rounded-lg transition-colors"
              >
                <Trash2 size={11} />
                Clear profile
              </button>
            )}
            <button
              onClick={() => setShowProfile((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg"
            >
              <Sparkles size={11} className="text-indigo-400" />
              Search profile
              {showProfile ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
          </div>
        </div>

        {/* Profile context panel */}
        {showProfile && (
          <div className="mt-3 p-3 bg-gray-900/60 border border-gray-800 rounded-xl text-xs space-y-2">
            {savedContext ? (
              <>
                <p className="text-gray-400 font-medium text-[11px] uppercase tracking-wide">Current search context</p>
                <p className="text-gray-300 leading-relaxed">{savedContext}</p>
                <p className="text-gray-600 text-[10px]">
                  Updated automatically as you chat. Used in all job scoring.
                </p>
              </>
            ) : (
              <p className="text-gray-600">
                No search context saved yet — chat with me to refine your preferences.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Quick Q&A panel (collapsed by default) */}
      <div className="shrink-0 px-4 md:px-6 py-2 border-b border-gray-800/50">
        <button
          onClick={() => setShowQA((v) => !v)}
          className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300"
        >
          {showQA ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          Structured questionnaire (alternative to chat)
          {questions.length > 0 && (
            <span className="bg-gray-800 text-gray-400 px-1.5 rounded-full">{questions.length} questions</span>
          )}
        </button>

        {showQA && (
          <div className="mt-3 space-y-4 pb-3">
            <div className="flex gap-2">
              <button
                onClick={() => generateQuestions()}
                disabled={generatingQs}
                className="flex items-center gap-1.5 text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg"
              >
                {generatingQs ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
                Generate questions from CV
              </button>
            </div>

            {questions.length > 0 && (
              <>
                <div className="space-y-3">
                  {questions.map((q: string, i: number) => (
                    <div key={i}>
                      <p className="text-xs text-gray-400 mb-1">{q}</p>
                      <textarea
                        value={qaAnswers[i] || ""}
                        onChange={(e) => setQaAnswers((prev) => ({ ...prev, [i]: e.target.value }))}
                        rows={2}
                        className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-xs outline-none focus:border-indigo-500 resize-none placeholder-gray-700"
                        placeholder="Your answer…"
                      />
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => saveAnswers()}
                  disabled={savingAnswers}
                  className="flex items-center gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg"
                >
                  {savingAnswers ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                  Save answers & update search profile
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Skills Gap Analysis */}
      <div className="shrink-0 px-4 md:px-6 py-3 border-b border-gray-800/50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <BarChart2 size={13} className="text-indigo-400" />
            <span className="font-medium">Skills Gap Analysis</span>
          </div>
          <button
            onClick={() => analyseGap()}
            disabled={analysingGap}
            className="flex items-center gap-1.5 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
          >
            {analysingGap ? <Loader2 size={11} className="animate-spin" /> : <BarChart2 size={11} />}
            Analyse my skills gap
          </button>
        </div>

        {analysingGap && (
          <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
            <Loader2 size={12} className="animate-spin" />
            Analysing your CV against matching jobs…
          </div>
        )}

        {!analysingGap && skillsGapMsg && (
          <p className="text-xs text-gray-500 italic py-1">{skillsGapMsg}</p>
        )}

        {!analysingGap && skillsGapResults && skillsGapResults.length > 0 && (
          <div className="mt-2 space-y-2 max-h-52 overflow-y-auto pr-1">
            {skillsGapResults.map((gap: any, i: number) => {
              const priorityStyles: Record<string, string> = {
                high:   "bg-red-900/40 text-red-300 border-red-700/40",
                medium: "bg-amber-900/40 text-amber-300 border-amber-700/40",
                low:    "bg-gray-800 text-gray-400 border-gray-700/40",
              };
              const p = (gap.priority || "low").toLowerCase();
              return (
                <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl px-3 py-2.5">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-xs font-semibold text-white">{gap.skill}</p>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${priorityStyles[p] ?? priorityStyles.low}`}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </span>
                  </div>
                  {gap.frequency != null && (
                    <p className="text-[11px] text-gray-500">
                      Appears in {gap.frequency} matching job{gap.frequency !== 1 ? "s" : ""}
                    </p>
                  )}
                  {gap.suggestion && (
                    <p className="text-[11px] text-gray-600 italic mt-0.5">{gap.suggestion}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-auto px-4 md:px-6 py-4 space-y-4">
        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} />
        ))}
        {sending && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0">
              <Bot size={13} className="text-indigo-400" />
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1.5">
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
      <div className="shrink-0 px-4 md:px-6 py-4 border-t border-gray-800">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell me what you're looking for…"
            className="flex-1 bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-indigo-500 transition-colors placeholder-gray-600"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
