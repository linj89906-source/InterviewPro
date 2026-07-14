import { useState } from 'react'
import ChatPage from './pages/ChatPage'
import Interview from './pages/Interview'
import Knowledge from './pages/Knowledge'
import Resume from './pages/Resume'
import Dashboard from './pages/Dashboard'

type Page = 'chat' | 'interview' | 'knowledge' | 'resume' | 'dashboard'

const navItems: { key: Page; label: string; icon: string }[] = [
  { key: 'chat', label: 'AI 对话', icon: '\uD83E\uDD16' },
  { key: 'interview', label: '模拟面试', icon: '\uD83C\uDFAF' },
  { key: 'resume', label: '简历优化', icon: '\uD83D\uDCC4' },
  { key: 'knowledge', label: '知识答疑', icon: '\uD83D\uDCDA' },
  { key: 'dashboard', label: '学习报告', icon: '\uD83D\uDCCA' },
]

export default function App() {
  const [page, setPage] = useState<Page>('chat')

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh' }}>
      <nav style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'0 24px',height:56,background:'var(--surface)',borderBottom:'1px solid var(--border)',flexShrink:0}}>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <span style={{fontSize:20,fontWeight:700,color:'var(--primary)'}}>InterviewPro</span>
          <span style={{fontSize:12,color:'var(--text-secondary)',padding:'2px 8px',background:'#eff6ff',borderRadius:10}}>Beta</span>
        </div>
        <div style={{display:'flex',gap:2}}>
          {navItems.map(item => (
            <button key={item.key} onClick={() => setPage(item.key)} style={{padding:'8px 16px',background:page===item.key?'var(--primary)':'transparent',color:page===item.key?'#fff':'var(--text-secondary)',borderRadius:'var(--radius)',fontWeight:page===item.key?600:400,display:'flex',alignItems:'center',gap:6}}>
              <span>{item.icon}</span> {item.label}
            </button>
          ))}
        </div>
      </nav>
      <main style={{flex:1,overflow:'auto'}}>
        {page === 'chat' && <ChatPage />}
        {page === 'interview' && <Interview />}
        {page === 'resume' && <Resume />}
        {page === 'knowledge' && <Knowledge />}
        {page === 'dashboard' && <Dashboard />}
      </main>
    </div>
  )
}
