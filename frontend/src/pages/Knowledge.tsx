import { useState, useRef, useEffect } from 'react'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: { id: number; title: string; category: string }[]
  mode?: string
}

const CATEGORIES = [
  { value: '', label: '不限领域' },
  { value: 'Java', label: 'Java' },
  { value: 'Python', label: 'Python' },
  { value: '算法', label: '算法' },
  { value: '数据库', label: '数据库' },
  { value: '网络', label: '网络' },
]

const WELCOME_MESSAGE: Message = {
  id: 0,
  role: 'assistant',
  content: '你好！我是编程知识助手，基于专业知识库为你解答计算机面试题。\n\n你可以问我：\n- HashMap 的底层实现原理？\n- Python 的 GIL 是什么？\n- 动态规划解题框架是什么？\n- TCP 三次握手的过程？\n- MySQL 索引优化技巧？',
}

const API_BASE = import.meta.env.VITE_API_URL || ""

export default function Knowledge() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [question, setQuestion] = useState('')
  const [category, setCategory] = useState('')
  const [mode, setMode] = useState<'rag' | 'chat'>('rag')
  const [loading, setLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const q = question.trim()
    if (!q || loading) return

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: q,
    }
    setMessages(prev => [...prev, userMsg])
    setQuestion('')
    setLoading(true)

    try {
      const endpoint = mode === 'rag' ? `${API_BASE}/api/knowledge/rag` : `${API_BASE}/api/knowledge/chat`
      const body: Record<string, string> = { question: q }
      if (mode === 'rag' && category) {
        (body as Record<string, string>).category = category
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '请求失败')
      }

      const data = await res.json()
      const assistantMsg: Message = {
        id: Date.now(),
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        mode: data.mode || 'chat',
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: `请求失败：${e instanceof Error ? e.message : '未知错误'}`,
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const getCategoryColor = (cat: string) => {
    const colors: Record<string, string> = {
      'Java': '#f97316', 'Python': '#3b82f6', '算法': '#8b5cf6',
      '数据库': '#22c55e', '网络': '#ef4444',
    }
    return colors[cat] || '#6b7280'
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24, height: 'calc(100vh - 56px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: 16, flexShrink: 0 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>编程知识助手</h2>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {mode === 'rag' ? '基于专业知识库的 RAG 增强问答' : '纯 AI 知识问答'}
        </p>
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1, overflow: 'auto', marginBottom: 16,
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius)', padding: 20,
      }}>
        {messages.map(msg => (
          <div key={msg.id} style={{ marginBottom: 20 }}>
            {/* Role label */}
            <div style={{
              fontSize: 12, fontWeight: 600, marginBottom: 6,
              color: msg.role === 'user' ? 'var(--primary)' : 'var(--success)',
            }}>
              {msg.role === 'user' ? '你' : 'AI 助手'}
              {msg.mode === 'rag' && msg.role === 'assistant' && (
                <span style={{
                  marginLeft: 8, fontSize: 10, padding: '1px 6px',
                  background: '#fef3c7', color: '#92400e', borderRadius: 8,
                }}>
                  RAG
                </span>
              )}
            </div>

            {/* Content */}
            <div style={{
              fontSize: 14, lineHeight: 1.8, whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {msg.content}
            </div>

            {/* Sources */}
            {msg.sources && msg.sources.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                  参考来源：
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {msg.sources.map(s => (
                    <span key={s.id} style={{
                      padding: '2px 8px', fontSize: 11,
                      background: '#f3f4f6', borderRadius: 10,
                      borderLeft: `3px solid ${getCategoryColor(s.category)}`,
                    }}>
                      [{s.category}] {s.title}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <div style={{
              width: 8, height: 8, background: 'var(--primary)',
              borderRadius: '50%', animation: 'pulse 1s infinite',
            }} />
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>思考中...</span>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div style={{ flexShrink: 0 }}>
        {/* Controls bar */}
        <div style={{
          display: 'flex', gap: 8, marginBottom: 8,
          alignItems: 'center', flexWrap: 'wrap',
        }}>
          {/* Mode toggle */}
          <div style={{
            display: 'flex', borderRadius: 'var(--radius)',
            border: '1px solid var(--border)', overflow: 'hidden',
          }}>
            {(['rag', 'chat'] as const).map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  padding: '6px 12px', fontSize: 12, fontWeight: mode === m ? 600 : 400,
                  background: mode === m ? 'var(--primary)' : 'var(--surface)',
                  color: mode === m ? '#fff' : 'var(--text-secondary)',
                  borderRadius: 0,
                }}
              >
                {m === 'rag' ? 'RAG 增强' : '纯 LLM'}
              </button>
            ))}
          </div>

          {/* Category selector */}
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            style={{
              padding: '6px 10px', fontSize: 12, borderRadius: 'var(--radius)',
              border: '1px solid var(--border)', background: 'var(--surface)',
              color: 'var(--text)',
            }}
          >
            {CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>

          {/* Clear button */}
          <button
            onClick={() => setMessages([WELCOME_MESSAGE])}
            style={{
              padding: '6px 12px', fontSize: 12, color: 'var(--text-secondary)',
              background: 'transparent', border: '1px solid var(--border)',
            }}
          >
            清空对话
          </button>
        </div>

        {/* Input row */}
        <div style={{ display: 'flex', gap: 8 }}>
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入技术问题，按 Enter 发送，Shift+Enter 换行..."
            rows={2}
            style={{
              flex: 1, resize: 'none', padding: '10px 14px',
              fontSize: 14, borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              fontFamily: 'inherit',
            }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !question.trim()}
            style={{
              padding: '0 24px', background: loading ? '#93c5fd' : 'var(--primary)',
              color: '#fff', fontWeight: 600, fontSize: 14,
              opacity: loading || !question.trim() ? 0.6 : 1,
            }}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}