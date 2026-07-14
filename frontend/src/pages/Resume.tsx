import { useState, useRef, DragEvent } from 'react'

interface AnalysisResult {
  quality_score: number
  score_breakdown: Record<string, number>
  basic_info: {
    name: string; education: string; major: string
    years: string; target_role: string; skills: string[]
  }
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  optimized_projects: { original: string; optimized: string; highlights: string[] }[]
  hr_first_impression: string
  overall_assessment: string
}

type Status = 'idle' | 'uploading' | 'analyzing' | 'done' | 'error'

const SCORE_LABELS: Record<string, string> = {
  '内容完整性': '内容完整',
  '表达清晰度': '表达清晰',
  '技术匹配度': '技术匹配',
  '成果量化度': '成果量化',
  '排版专业性': '排版专业',
}

const API_BASE = import.meta.env.VITE_API_URL || ""

export default function Resume() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')
    setError('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/api/resume/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '上传失败')
      }
      const data = await res.json()
      setStatus('analyzing')
      await pollResult(data.id)
    } catch (e: any) {
      setError(e.message || '上传失败')
      setStatus('error')
    }
  }

  const pollResult = async (analysisId: number) => {
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 2000))
      try {
        const res = await fetch(`${API_BASE}/api/resume/${analysisId}`)
        if (!res.ok) continue
        const data = await res.json()
        if (data.status === 'completed') {
          setResult({
            quality_score: data.quality_score || 0,
            score_breakdown: data.hr_feedback?.score_breakdown || {},
            basic_info: data.basic_info || {},
            strengths: data.strengths || [],
            weaknesses: data.weaknesses || [],
            suggestions: data.suggestions || [],
            optimized_projects: data.optimized_projects || [],
            hr_first_impression: data.hr_feedback?.first_impression || '',
            overall_assessment: data.hr_feedback?.overall_assessment || '',
          })
          setStatus('done')
          return
        }
        if (data.status === 'failed') {
          throw new Error(data.error_message || '分析失败')
        }
      } catch (e: any) {
        setError(e.message || '分析失败')
        setStatus('error')
        return
      }
    }
    setError('分析超时，请重试')
    setStatus('error')
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f && (f.name.endsWith('.pdf') || f.name.endsWith('.docx'))) {
      setFile(f)
      setResult(null)
      setStatus('idle')
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setResult(null)
      setStatus('idle')
    }
  }

  const getScoreColor = (s: number) =>
    s >= 80 ? 'var(--success)' : s >= 60 ? 'var(--warning)' : 'var(--danger)'

  const getScoreBg = (s: number) =>
    s >= 80 ? '#f0fdf4' : s >= 60 ? '#fffbeb' : '#fef2f2'

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
        AI 简历优化
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
        上传 PDF 或 DOCX 格式的简历，AI 会从多个维度进行评分并给出优化建议。
      </p>

      {/* 上传区域 */}
      <div
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? 'var(--primary)' : 'var(--border)'}`,
          borderRadius: 'var(--radius)',
          padding: '40px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragOver ? '#eff6ff' : 'var(--surface)',
          transition: 'all .15s',
          marginBottom: 20,
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        {file ? (
          <div>
            <div style={{ fontSize: 28, marginBottom: 8 }}>&#128196;</div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>{file.name}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
              {(file.size / 1024).toFixed(1)} KB · 点击更换文件
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#128229;</div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>
              拖拽简历到此处，或点击选择文件
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
              支持 PDF 和 DOCX 格式，最大 10MB
            </div>
          </div>
        )}
      </div>

      {/* 上传按钮 */}
      {file && status === 'idle' && (
        <button
          onClick={(e) => { e.stopPropagation(); handleUpload() }}
          style={{
            width: '100%', padding: '12px 0', background: 'var(--primary)',
            color: '#fff', fontWeight: 600, fontSize: 15,
          }}
        >
          开始 AI 分析
        </button>
      )}

      {/* 加载中 */}
      {(status === 'uploading' || status === 'analyzing') && (
        <div style={{
          textAlign: 'center', padding: 32, color: 'var(--text-secondary)'
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>&#9203;</div>
          <div style={{ fontWeight: 600 }}>
            {status === 'uploading' ? '正在上传并解析简历...' : 'AI 正在分析你的简历...'}
          </div>
          <div style={{ fontSize: 12, marginTop: 4 }}>
            {status === 'analyzing' ? '预计需要 10-30 秒' : ''}
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {status === 'error' && (
        <div style={{
          padding: 16, background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: 'var(--radius)', color: 'var(--danger)', fontSize: 14,
          marginTop: 16
        }}>
          {error}
          <button
            onClick={() => { setStatus('idle'); setError('') }}
            style={{ marginLeft: 12, background: 'transparent', color: 'var(--danger)', textDecoration: 'underline' }}
          >
            重试
          </button>
        </div>
      )}

      {/* 分析结果 */}
      {status === 'done' && result && (
        <div style={{ marginTop: 24 }}>
          {/* 综合评分卡片 */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: getScoreBg(result.quality_score),
            border: `1px solid ${getScoreColor(result.quality_score)}33`,
            borderRadius: 'var(--radius)', padding: '24px 28px', marginBottom: 24,
          }}>
            <div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>
                综合质量评分
              </div>
              <div style={{ fontSize: 42, fontWeight: 800, color: getScoreColor(result.quality_score), lineHeight: 1 }}>
                {Math.round(result.quality_score)}
                <span style={{ fontSize: 16, fontWeight: 400 }}> / 100</span>
              </div>
            </div>
            {/* 各维度评分 */}
            <div style={{ flex: 1, maxWidth: 360, marginLeft: 40 }}>
              {Object.entries(result.score_breakdown).map(([key, val]) => (
                <div key={key} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {SCORE_LABELS[key] || key}
                    </span>
                    <span style={{ fontWeight: 600, color: getScoreColor(val) }}>
                      {Math.round(val)}分
                    </span>
                  </div>
                  <div style={{ height: 4, background: '#e5e7eb', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', borderRadius: 2,
                      width: `${(val / 25) * 100}%`,
                      background: getScoreColor(val),
                      transition: 'width .4s',
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 基本信息 */}
          {result.basic_info?.name && (
            <Section title="基本信息">
              <InfoGrid items={[
                ['姓名', result.basic_info.name],
                ['学历', result.basic_info.education],
                ['专业', result.basic_info.major],
                ['工作年限', result.basic_info.years],
                ['求职意向', result.basic_info.target_role],
              ].filter(([, v]) => v) as [string, string][]} />
              {result.basic_info.skills?.length > 0 && (
                <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {result.basic_info.skills.map((s, i) => (
                    <span key={i} style={{
                      padding: '3px 10px', background: '#eff6ff', color: 'var(--primary)',
                      borderRadius: 12, fontSize: 12, fontWeight: 500,
                    }}>{s}</span>
                  ))}
                </div>
              )}
            </Section>
          )}

          {/* 优势 */}
          {result.strengths.length > 0 && (
            <Section title="简历优势" icon="&#x2705;">
              <List items={result.strengths} color="var(--success)" bg="#f0fdf4" border="#bbf7d0" />
            </Section>
          )}

          {/* 不足 */}
          {result.weaknesses.length > 0 && (
            <Section title="不足之处" icon="&#x26A0;&#xFE0F;">
              <List items={result.weaknesses} color="var(--warning)" bg="#fffbeb" border="#fde68a" />
            </Section>
          )}

          {/* 建议 */}
          {result.suggestions.length > 0 && (
            <Section title="修改建议" icon="&#x1F4DD;">
              <List items={result.suggestions} color="var(--primary)" bg="#eff6ff" border="#bfdbfe" numbered />
            </Section>
          )}

          {/* 项目经历优化 */}
          {result.optimized_projects.length > 0 && (
            <Section title="项目经历 STAR 改写" icon="&#x2728;">
              {result.optimized_projects.map((proj, i) => (
                <div key={i} style={{
                  background: 'var(--surface)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', padding: 16, marginBottom: 12,
                }}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, fontWeight: 600 }}>
                    项目 {i + 1}
                  </div>
                  {proj.original && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                        原文：
                      </div>
                      <div style={{
                        fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7,
                        padding: '8px 12px', background: '#f9fafb', borderRadius: 'var(--radius)',
                        borderLeft: '3px solid #d1d5db',
                      }}>
                        {proj.original}
                      </div>
                    </div>
                  )}
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--success)', marginBottom: 4, fontWeight: 600 }}>
                      STAR 改写后：
                    </div>
                    <div style={{
                      fontSize: 13, lineHeight: 1.7,
                      padding: '8px 12px', background: '#f0fdf4', borderRadius: 'var(--radius)',
                      borderLeft: '3px solid var(--success)',
                    }}>
                      {proj.optimized}
                    </div>
                  </div>
                  {proj.highlights?.length > 0 && (
                    <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {proj.highlights.map((h, j) => (
                        <span key={j} style={{
                          padding: '2px 8px', background: '#fef3c7', color: '#92400e',
                          borderRadius: 10, fontSize: 11,
                        }}>{h}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </Section>
          )}

          {/* HR 评价 */}
          {(result.hr_first_impression || result.overall_assessment) && (
            <Section title="HR 快速评估" icon="&#x1F465;">
              {result.hr_first_impression && (
                <div style={{
                  padding: 14, background: '#fdf2f8', border: '1px solid #fbcfe8',
                  borderRadius: 'var(--radius)', fontSize: 13, lineHeight: 1.7,
                  marginBottom: 10, borderLeft: '3px solid #ec4899',
                }}>
                  <div style={{ fontWeight: 600, fontSize: 11, color: '#be185d', marginBottom: 4 }}>
                    10秒浏览第一印象：
                  </div>
                  {result.hr_first_impression}
                </div>
              )}
              {result.overall_assessment && (
                <div style={{
                  padding: 14, background: '#f5f3ff', border: '1px solid #ddd6fe',
                  borderRadius: 'var(--radius)', fontSize: 13, lineHeight: 1.7,
                  borderLeft: '3px solid #8b5cf6',
                }}>
                  <div style={{ fontWeight: 600, fontSize: 11, color: '#6d28d9', marginBottom: 4 }}>
                    综合评价：
                  </div>
                  {result.overall_assessment}
                </div>
              )}
            </Section>
          )}

          {/* 再来一份 */}
          <button
            onClick={() => { setFile(null); setResult(null); setStatus('idle') }}
            style={{
              marginTop: 16, padding: '10px 24px',
              background: 'transparent', color: 'var(--primary)',
              border: '1px solid var(--primary)', fontWeight: 500,
            }}
          >
            分析另一份简历
          </button>
        </div>
      )}
    </div>
  )
}

/* --- 子组件 --- */

function Section({ title, icon, children }: { title: string; icon?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <h3 style={{
        fontSize: 15, fontWeight: 600, marginBottom: 12,
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        {icon && <span>{icon}</span>}
        {title}
      </h3>
      {children}
    </div>
  )
}

function InfoGrid({ items }: { items: [string, string][] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
      {items.map(([label, value]) => (
        <div key={label} style={{
          padding: '8px 12px', background: '#f9fafb', borderRadius: 'var(--radius)',
          fontSize: 13,
        }}>
          <span style={{ color: 'var(--text-secondary)' }}>{label}：</span>
          <span style={{ fontWeight: 500 }}>{value}</span>
        </div>
      ))}
    </div>
  )
}

function List({ items, color, bg, border, numbered }: {
  items: string[]; color: string; bg: string; border: string; numbered?: boolean
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {items.map((item, i) => (
        <div key={i} style={{
          padding: '10px 14px', background: bg, border: `1px solid ${border}`,
          borderRadius: 'var(--radius)', fontSize: 13, lineHeight: 1.6,
        }}>
          {numbered && (
            <span style={{ color, fontWeight: 600, marginRight: 6 }}>{i + 1}.</span>
          )}
          {item}
        </div>
      ))}
    </div>
  )
}
