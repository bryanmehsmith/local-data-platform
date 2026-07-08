import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Send, Loader2, Bot, User } from "lucide-react";
import { apiGet, apiPost } from "../api/client";
import type { ChatModel, ChatResponse } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input, Select } from "../components/ui/Input";
import { EmptyState } from "../components/ui/Feedback";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatPage() {
  const [model, setModel] = useState("lakehouse_rag");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const modelsQuery = useQuery({
    queryKey: ["chat-models"],
    queryFn: () => apiGet<ChatModel[]>("/chat/models"),
  });

  const chatMutation = useMutation({
    mutationFn: (message: string) => apiPost<ChatResponse>("/chat/completions", { message, model }),
    onSuccess: (data) => setMessages((m) => [...m, { role: "assistant", content: data.reply }]),
    onError: (err: Error) =>
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${err.message}` }]),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatMutation.isPending]);

  const send = () => {
    if (!input.trim() || chatMutation.isPending) return;
    setMessages((m) => [...m, { role: "user", content: input }]);
    chatMutation.mutate(input);
    setInput("");
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <PageHeader
        title="Chat"
        description="Ask questions answered by RAG or live text-to-SQL."
        actions={
          <Select value={model} onChange={(e) => setModel(e.target.value)} className="w-56">
            {modelsQuery.data?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </Select>
        }
      />

      <Card className="flex flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 && <EmptyState message="Ask a question to get started." />}
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <div
                className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400"
                }`}
              >
                {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-800 dark:bg-slate-800 dark:text-slate-200"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {chatMutation.isPending && (
            <div className="flex items-center gap-2 pl-10 text-sm text-gray-400 dark:text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking...
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex items-center gap-2 border-t border-gray-100 p-3 dark:border-slate-800">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask a question..."
            className="flex-1"
          />
          <Button onClick={send} disabled={!input.trim()} loading={chatMutation.isPending}>
            <Send className="h-4 w-4" />
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
}
