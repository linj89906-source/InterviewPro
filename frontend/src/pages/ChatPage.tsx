import { useState, useRef, useEffect } from 'react'

interface Hotel {
  name: string; distance: string; price: string; type: string; reason: string
}
interface ChatSource { id: number; title: string; category: string }
interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  hotels?: Hotel[]
  location?: string
  transport?: string
  suggestion?: string
  sources?: ChatSource[]
  intent?: string
  mode?: string
}

const INTENT_LABELS: Record<string, string> = {
  coding: '技术问答', location: '出行规划', resume: '简历', interview: '面试',
  general: '对话',
}

const SUGGESTIONS = [
  'Redis 为什么采用单线程模型？',
  'Java 后端面试准备技巧',
  '杭州阿里巴巴附近面试住宿推荐',
  'Python 开发者简历优化建议',
  '前端岗位模拟面试',
]

const API_BASE = import.meta.env.VITE_API_URL || ""

export default function ChatPage() {
  const [msgs, setMsgs] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [convId, setConvId] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = async (msg?: string) => {
    const text = (msg || input).trim()
    if (!text || loading) return
    const u: ChatMsg = { role: 'user', content: text }
    setMsgs(prev => [...prev, u])
    setInput('')
    setLoading(true)
    try {
      const body: any = { message: text, user_id: 1 }
      if (convId) body.conversation_id = convId
      const res = await fetch(`${API_BASE}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await res.json()
      if (data.conversation_id) setConvId(data.conversation_id)
      const ai: ChatMsg = {
        role: 'assistant', content: data.reply || '',
        hotels: data.data?.hotels || [], location: data.data?.location || '',
        transport: data.data?.transport || '', suggestion: data.data?.suggestion || '',
        sources: data.data?.sources || [], intent: data.intent, mode: data.data?.mode,
      }
      setMsgs(prev => [...prev, ai])
    } catch (e) {
      setMsgs(prev => [...prev, { role: 'assistant', content: '网络错误，请确认后端已启动' }])
    }
    setLoading(false)
  }

  const intentBadge = (intent?: string) => {
    if (!intent || intent === 'general') return null
    const colors: Record<string,string> = {coding:'#eff6ff',location:'#fef3c7',resume:'#fce7f3',interview:'#dcfce7' }
    const tColors: Record<string,string> = {coding:'#1e40af',location:'#92400e',resume:'#9d174d',interview:'#166534' }
    return <span style={{fontSize:10,padding:'1px 6px',background:colors[intent]||'#f3f4f6',color:tColors[intent]||'#374151',borderRadius:8,fontWeight:600,marginBottom:6,display:'inline-block' }}>{INTENT_LABELS[intent] || intent}</span>
  }

  const render住宿推荐 = (hotels: Hotel[]) => (
    <div style={{marginTop:12 }}>
      <div style={{fontSize:13,fontWeight:600,color:'var(--text-secondary)',marginBottom:8 }}>住宿推荐 ({hotels.length})</div>
      <div style={{display:'flex',flexDirection:'column',gap:6 }}>
        {hotels.map((h,i) => (
          <div key={i} style={{padding:'10px 12px',background:'#f9fafb',border:'1px solid var(--border)',borderRadius:'var(--radius)',fontSize:13 }}>
            <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:4 }}>
              <span style={{fontWeight:600 }}>{h.name}</span>
              <span style={{fontSize:11,padding:'1px 6px',background:h.price==='budget'?'#dcfce7':'#eff6ff',color:h.price==='budget'?'#166534':'#1e40af',borderRadius:8 }}>{h.price}</span>
              <span style={{fontSize:11,padding:'1px 6px',background:'#f3f4f6',color:'var(--text-secondary)',borderRadius:8 }}>{h.type}</span>
            </div>
            <div style={{display:'flex',gap:16,fontSize:12,color:'var(--text-secondary)' }}>
              <span>距离: {h.distance}</span>
              <span style={{color:'var(--primary)' }}>{h.reason}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderSources = (sources: ChatSource[]) => (
    <div style={{marginTop:10,fontSize:12,color:'var(--text-secondary)',borderTop:'1px solid var(--border)',paddingTop:8 }}>
      <span style={{fontWeight:600 }}>参考来源: </span>
      {sources.map((s,i) => <span key={i} style={{marginRight:12,background:'#f3f4f6',padding:'1px 6px',borderRadius:4 }}>{s.category}/{s.title}</span>)}
    </div>
  )


  return (
    <div style={{display:'flex',flexDirection:'column',height:'100%',maxWidth:800,margin:'0 auto' }}>
      <div style={{padding:'14px 20px',borderBottom:'1px solid var(--border)',background:'var(--surface)',flexShrink:0,display:'flex',alignItems:'center',justifyContent:'space-between' }}>
        <div style={{display:'flex',alignItems:'center',gap:8 }}>
          <h3 style={{fontSize:16,fontWeight:600 }}>面试助手 AI</h3>
          <span style={{fontSize:11,color:'var(--text-secondary)',padding:'2px 8px',background:'#f3f4f6',borderRadius:8 }}>智能调度</span>
        </div>
        {convId && <button onClick={()=>{setMsgs([]);setConvId(null)}} style={{fontSize:12,color:'var(--text-secondary)',background:'transparent' }}>新对话</button>}
      </div>

      <div style={{flex:1,overflowY:'auto',padding:'16px 20px' }}>
        {msgs.length === 0 ? (
          <div style={{textAlign:'center',paddingTop:60 }}>
            <div style={{fontSize:40,marginBottom:12 }}>\uD83E\uDD16</div>
            <div style={{fontSize:16,fontWeight:600,marginBottom:6 }}>你的 AI 面试助手</div>
            <div style={{fontSize:13,color:'var(--text-secondary)',marginBottom:28 }}>自动路由：简历教练 | 面试准备 | 技术问答 | 出行规划</div>
            <div style={{display:'flex',flexWrap:'wrap',gap:8,justifyContent:'center' }}>
              {SUGGESTIONS.map((s,i) => (
                <button key={i} onClick={() => send(s)} style={{padding:'8px 14px',fontSize:13,background:'var(--surface)',border:'1px solid var(--border)',color:'var(--text)',borderRadius:'var(--radius)',maxWidth:320,textAlign:'left' }}>{s}</button>
              ))}
            </div>
          </div>
        ) : (
          msgs.map((m, i) => (
            <div key={i} style={{marginBottom:16 }}>
              {m.role === 'user' ? (
                <div style={{display:'flex',justifyContent:'flex-end' }}>
                  <div style={{maxWidth:'80%',padding:'10px 14px',background:'var(--primary)',color:'#fff',borderRadius:'12px 12px 4px 12px',fontSize:14 }}>{m.content}</div>
                </div>
              ) : (
                <div style={{display:'flex',gap:10 }}>
                  <div style={{width:32,height:32,borderRadius:'50%',background:'#eff6ff',display:'flex',alignItems:'center',justifyContent:'center',fontSize:14,flexShrink:0 }}>\uD83E\uDD16</div>
                  <div style={{maxWidth:'85%',padding:'12px 16px',background:'var(--surface)',border:'1px solid var(--border)',borderRadius:'4px 12px 12px 12px' }}>
                    {intentBadge(m.intent)}
                    <div style={{whiteSpace:'pre-wrap',lineHeight:1.7,fontSize:14 }}>{m.content}</div>
                    {m.sources && m.sources.length > 0 && renderSources(m.sources)}
                    {m.hotels && m.hotels.length > 0 && render住宿推荐(m.hotels)}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div style={{display:'flex',gap:10,marginBottom:16 }}>
            <div style={{width:32,height:32,borderRadius:'50%',background:'#eff6ff',display:'flex',alignItems:'center',justifyContent:'center',fontSize:14 }}>\uD83E\uDD16</div>
            <div style={{padding:'12px 16px',background:'var(--surface)',border:'1px solid var(--border)',borderRadius:'4px 12px 12px 12px',fontSize:14,color:'var(--text-secondary)' }}>思考中...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{padding:'12px 20px',borderTop:'1px solid var(--border)',background:'var(--surface)',flexShrink:0 }}>
        <div style={{display:'flex',gap:8 }}>
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
            placeholder='输入任何问题：简历优化、模拟面试、编程问答、面试住宿推荐...'
            style={{flex:1,padding:'10px 14px' }} disabled={loading} />
          <button onClick={() => send()} disabled={loading || !input.trim()}
            style={{padding:'10px 20px',background:loading?'#e5e7eb':'var(--primary)',color:loading?'#9ca3af':'#fff',fontWeight:600,fontSize:14 }}>
            {loading ? '...' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}
