import { useState, useEffect } from 'react'

interface SessionSummary {
  id: number
  role: string
  mode: string
  status: string
  total_questions: number
  score_avg: number
  created_at: string
}

interface UserStats {
  username: string
  target_role: string
  total_sessions: number
  total_questions: number
  avg_score: number
}

const DOMAIN_STATS = [
  { domain: '操作系统', score: 72, count: 15 },
  { domain: '计算机网络', score: 85, count: 20 },
  { domain: '数据库', score: 68, count: 12 },
  { domain: '数据结构', score: 90, count: 25 },
  { domain: '算法', score: 75, count: 18 },
  { domain: 'Java', score: 82, count: 22 },
  { domain: '系统设计', score: 65, count: 8 },
  { domain: '并发编程', score: 70, count: 10 },
]

const INTERVIEW_TIPS = [
  '面试前先了解公司技术栈和业务方向',
  'STAR 法则：情境(Situation)→任务(Task)→行动(Action)→结果(Result)',
  '遇到不会的问题坦诚说明，展示你的学习思路',
  '反问环节是展示你对岗位理解的好机会',
  '系统设计题先确认需求，再逐步展开架构',
  '算法题先讲思路再写代码，写完后主动测试边界情况',
]

const API_BASE = import.meta.env.VITE_API_URL || ""

export default function Dashboard() {
  const [stats, setStats] = useState<UserStats | null>(null)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [statsRes, sessionsRes] = await Promise.all([
        fetch(`${API_BASE}/api/user/1/stats`),
        fetch(`${API_BASE}/api/interview/sessions/1`)
      ])
      if (statsRes.ok) setStats(await statsRes.json())
      if (sessionsRes.ok) setSessions(await sessionsRes.json())
    } catch (e) {
      console.error('Failed to load dashboard:', e)
    }
    setLoading(false)
  }

  const getScoreColor = (score: number) =>
    score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--warning)' : 'var(--danger)'

  const getModeLabel = (mode: string) =>
    mode === 'practice' ? '练习' : mode === 'mock' ? '模拟' : '快速'

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
        加载中...
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      {/* Stats overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        {[
          { label: '面试场次', value: stats?.total_sessions ?? 0, unit: '次', color: 'var(--primary)' },
          { label: '答题数量', value: stats?.total_questions ?? 0, unit: '题', color: '#8b5cf6' },
          { label: '平均得分', value: stats?.avg_score ?? 0, unit: '分', color: 'var(--success)' },
          { label: '目标岗位', value: stats?.target_role || '未设置', unit: '', color: '#f59e0b' },
        ].map((item, i) => (
          <div key={i} style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', padding: '20px 16px'
          }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>{item.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: item.color }}>
              {item.value}{item.unit && <span style={{ fontSize: 14, fontWeight: 400, color: 'var(--text-secondary)' }}> {item.unit}</span>}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 28 }}>
        {/* Domain breakdown */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>📊 知识领域掌握度</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {DOMAIN_STATS.map(d => (
              <div key={d.domain}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
                  <span style={{ fontWeight: 500 }}>{d.domain}</span>
                  <span style={{
                    color: getScoreColor(d.score), fontWeight: 600
                  }}>{d.score}分 · {d.count}题</span>
                </div>
                <div style={{ height: 6, background: '#f3f4f6', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 3,
                    width: `${d.score}%`,
                    background: d.score >= 80
                      ? 'linear-gradient(90deg, #22c55e, #16a34a)'
                      : d.score >= 60
                        ? 'linear-gradient(90deg, #f59e0b, #d97706)'
                        : 'linear-gradient(90deg, #ef4444, #dc2626)',
                    transition: 'width .3s'
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interview tips */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>💡 面试小贴士</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {INTERVIEW_TIPS.map((tip, i) => (
              <div key={i} style={{
                padding: '10px 12px', background: '#fffbeb', borderRadius: 'var(--radius)',
                fontSize: 13, lineHeight: 1.6, border: '1px solid #fde68a'
              }}>
                <span style={{ color: '#d97706', fontWeight: 600, marginRight: 6 }}>{i + 1}.</span>
                {tip}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent sessions */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 20 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>📋 最近面试记录</h3>
        {sessions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-secondary)', fontSize: 14 }}>
            还没有面试记录，去<a href="#" onClick={() => window.location.hash = '#interview'} style={{ color: 'var(--primary)' }}>开始训练</a>吧
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sessions.map(s => (
              <div key={s.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '12px 16px', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', fontSize: 13
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{
                    padding: '3px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
                    background: s.mode === 'mock' ? '#fef2f2' : s.mode === 'practice' ? '#eff6ff' : '#f0fdf4',
                    color: s.mode === 'mock' ? 'var(--danger)' : s.mode === 'practice' ? 'var(--primary)' : 'var(--success)'
                  }}>
                    {getModeLabel(s.mode)}
                  </span>
                  <span style={{ fontWeight: 500 }}>{s.role}</span>
                  {s.role && <span style={{ color: 'var(--text-secondary)' }}>面试</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{s.total_questions} 题</span>
                  <span style={{
                    fontWeight: 600, color: getScoreColor(s.score_avg)
                  }}>
                    {s.score_avg > 0 ? `${Math.round(s.score_avg)}分` : '进行中'}
                  </span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                    {s.created_at ? new Date(s.created_at).toLocaleDateString('zh-CN') : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}