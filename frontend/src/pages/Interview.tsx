import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'interviewer' | 'user'
  content: string
  score?: number
  feedback?: {
    strengths: string[]
    weaknesses: string[]
    reference_answer?: string
    next_direction?: string
  }
}

const ROLES = ['后端开发', '前端开发', '算法工程师', '测试开发', 'DevOps', '全栈开发', '客户端开发', '数据工程师']
const MODES: { key: string; label: string; desc: string }[] = [
  { key: 'practice', label: '练习模式', desc: '温和引导，答错时给提示' },
  { key: 'mock', label: '模拟面试', desc: '严格计时，真实面试压力' },
  { key: 'quick', label: '快速刷题', desc: '一问一答，快速评分' },
]

const API_BASE = import.meta.env.VITE_API_URL || ""

export default function Interview() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [role, setRole] = useState('后端开发')
  const [mode, setMode] = useState('practice')
  const [started, setStarted] = useState(false)
  const [showSettings, setShowSettings] = useState(true)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const startInterview = async () => {
    setLoading(true)
    setShowSettings(false)
    setMessages([])
    try {
      const res = await fetch(`${API_BASE}/api/interview/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 1, role, mode })
      })
      const data = await res.json()
      setSessionId(data.session_id)
      const msg = data.message
      setMessages([{
        role: 'interviewer',
        content: typeof msg.content === 'string' ? msg.content : '面试准备好了吗？让我们开始吧。',
        score: msg.score,
        feedback: msg.feedback_detail
      }])
      setStarted(true)
    } catch (e) {
      setMessages([{ role: 'interviewer', content: '面试官正在赶来...请确保后端服务已启动。' }])
      setStarted(true)
    }
    setLoading(false)
  }

  const sendMessage = async () => {
    if (!input.trim() || loading || !sessionId) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const history = messages.map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content
      }))

      const res = await fetch(`${API_BASE}/api/interview/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: input, history })
      })
      const data = await res.json()
      const result = data.message

      const aiMsg: Message = {
        role: 'interviewer',
        content: result.content || '好的，继续说...',
        score: result.score,
        feedback: result.feedback_detail
      }
      setMessages(prev => [...prev, aiMsg])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'interviewer',
        content: '抱歉，面试官暂时断线了。请检查后端服务。'
      }])
    }
    setLoading(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {showSettings ? (
        <div style={{ maxWidth: 480, margin: '60px auto', width: '100%' }}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🎯</div>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>开始你的面试训练</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>选择目标岗位和模式，AI 面试官将为你模拟真实面试</p>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>目标岗位</label>
            <select value={role} onChange={e => setRole(e.target.value)}
              style={{ width: '100%', padding: '10px 12px', background: 'var(--surface)' }}>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          <div style={{ marginBottom: 28 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>面试模式</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {MODES.map(m => (
                <button key={m.key}
                  onClick={() => setMode(m.key)}
                  style={{
                    textAlign: 'left', padding: '12px 16px',
                    background: mode === m.key ? '#eff6ff' : 'var(--surface)',
                    border: mode === m.key ? '2px solid var(--primary)' : '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                  }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{m.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <button onClick={startInterview} disabled={loading}
            style={{
              width: '100%', padding: '14px', background: 'var(--primary)',
              color: '#fff', fontSize: 16, fontWeight: 600, borderRadius: 'var(--radius)'
            }}>
            {loading ? '面试官准备中...' : '开始面试'}
          </button>
        </div>
      ) : (
        <>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 0', borderBottom: '1px solid var(--border)', marginBottom: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 18 }}>🤖</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>AI 面试官</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {role} · {MODES.find(m => m.key === mode)?.label}
                </div>
              </div>
            </div>
            <button onClick={() => { setShowSettings(true); setStarted(false); setSessionId(null) }}
              style={{ padding: '6px 12px', background: 'transparent', color: 'var(--text-secondary)', fontSize: 13 }}>
              结束面试
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 16 }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: 'flex', gap: 10, marginBottom: 20,
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
              }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: msg.role === 'interviewer' ? 'var(--primary)' : 'var(--success)',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14, flexShrink: 0
                }}>
                  {msg.role === 'interviewer' ? 'AI' : '我'}
                </div>
                <div style={{ maxWidth: '75%' }}>
                  <div style={{
                    padding: '12px 16px', borderRadius: 'var(--radius)',
                    background: msg.role === 'interviewer' ? 'var(--surface)' : '#eff6ff',
                    border: '1px solid var(--border)', fontSize: 14, lineHeight: 1.7,
                    whiteSpace: 'pre-wrap'
                  }}>
                    {msg.content}
                  </div>
                  {msg.score != null && msg.score > 0 && (
                    <div style={{
                      marginTop: 6, padding: '10px 12px',
                      background: msg.score >= 80 ? '#f0fdf4' : msg.score >= 60 ? '#fffbeb' : '#fef2f2',
                      borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13
                    }}>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>
                        评分: <span style={{
                          color: msg.score >= 80 ? 'var(--success)' : msg.score >= 60 ? 'var(--warning)' : 'var(--danger)'
                        }}>{msg.score}/100</span>
                      </div>
                      {msg.feedback?.strengths?.length ? (
                        <div style={{ marginBottom: 4 }}>
                          ✅ 优点: {msg.feedback.strengths.join('；')}
                        </div>
                      ) : null}
                      {msg.feedback?.weaknesses?.length ? (
                        <div style={{ marginBottom: 4 }}>
                          ⚠️ 不足: {msg.feedback.weaknesses.join('；')}
                        </div>
                      ) : null}
                      {msg.feedback?.reference_answer ? (
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                          📝 参考要点: {msg.feedback.reference_answer}
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%', background: 'var(--primary)',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14
                }}>AI</div>
                <div style={{ padding: '12px 16px', background: 'var(--surface)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', fontSize: 14, color: 'var(--text-secondary)' }}>
                  面试官正在思考...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div style={{
            display: 'flex', gap: 8, padding: '12px 0',
            borderTop: '1px solid var(--border)', flexShrink: 0
          }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的回答... (Enter 发送，Shift+Enter 换行)"
              rows={2}
              style={{
                flex: 1, resize: 'none', padding: '10px 12px',
                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                outline: 'none', fontSize: 14
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              style={{
                padding: '0 20px', background: !input.trim() ? '#e5e7eb' : 'var(--primary)',
                color: !input.trim() ? '#9ca3af' : '#fff', fontWeight: 600, fontSize: 14, borderRadius: 'var(--radius)',
                alignSelf: 'flex-end', height: 44
              }}>
              发送
            </button>
          </div>
        </>
      )}
    </div>
  )
}