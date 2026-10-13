import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Breadcrumb, Button, Card, Collapse, Empty, Grid, Spin, Tree, Typography, Alert, Tag } from 'antd'
import type { DataNode } from 'antd/es/tree'
import { FileTextOutlined, LinkOutlined, UnorderedListOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'

const { Title, Text, Paragraph } = Typography

/**
 * 文档中心：SillyTavern 官方文档的中文译本（`tools/gen_docs_zh.py` 的产物）。
 *
 * 两条与后端约定好的规则（改这里前先看 backend/api/docs.py）：
 *   · URL = `/docs` + 文档路由，如 `/docs/usage/macros/`；树上的 key 就是文档路由本身。
 *   · 正文里的图片有两种写法——根相对（`/static/xxx.png`）与相对当前篇（`../img/x.png`），
 *     都要交给 `/api/docs/asset`（它按官方文档仓库的根来解析），**不能**直接交给浏览器。
 */

interface TreeNode {
  route: string
  title: string
  icon?: string
  hasPage?: boolean
  children?: TreeNode[]
}

interface TreeMeta {
  rootTitle: string
  commit: string
  pages: number
  articles: number
  synthetic: number
  routes: string[]
  tree: TreeNode
}

interface Article {
  route: string
  title: string
  synthetic: boolean
  /** 顶层节点：页头已经写了标题，正文里的 H1 不再重复渲染 */
  topLevel?: boolean
  source: string
  content: string
}

const API = '/api/docs'

/** 树节点 → antd Tree 数据 */
function toTreeData(nodes: TreeNode[]): DataNode[] {
  return nodes.map(n => ({
    key: n.route,
    title: n.title,
    children: n.children && n.children.length ? toTreeData(n.children) : undefined,
  }))
}

/** 一篇文档的相对图片路径 → 相对该文档所在的目录解析（与后端 asset 接口的根对齐） */
function resolveAssetPath(route: string, src: string): string {
  const segs = route.split('/').filter(Boolean)
  segs.pop()
  for (const part of src.split('/')) {
    if (!part || part === '.') continue
    if (part === '..') segs.pop()
    else segs.push(part)
  }
  return '/' + segs.join('/')
}

function assetUrl(path: string) {
  return `${API}/asset?path=${encodeURIComponent(path)}`
}

export default function DocsPage() {
  const navigate = useNavigate()
  // 路由参数是 `/docs/*` 后面的部分：`/docs/usage/macros/` → `usage/macros`
  const params = useParams()
  const splat = (params['*'] || '').trim()
  const route = splat ? `/${splat.replace(/^\/+|\/+$/g, '')}/` : '/'

  const [meta, setMeta] = useState<TreeMeta | null>(null)
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // 窄屏（<768px）下目录**默认收起**：树一展开就把首屏占满，正文被推到下面，
  // 而手机上来是要读文档的。桌面维持常驻（与 MainLayout 用同一套断点判断）。
  const screens = Grid.useBreakpoint()
  const isMobile = screens.md === false
  const [tocOpen, setTocOpen] = useState(false)
  useEffect(() => {
    setTocOpen(!isMobile)
  }, [isMobile])

  // ① 拉导航树（只拉一次）
  useEffect(() => {
    let alive = true
    fetch(`${API}/tree`)
      .then(async r => {
        if (!r.ok) throw new Error(`导航树加载失败（HTTP ${r.status}）`)
        return (await r.json()) as TreeMeta
      })
      .then(data => {
        if (alive) setMeta(data)
      })
      .catch(e => {
        if (alive) setError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      alive = false
    }
  }, [])

  // ② 拉当前这篇正文
  useEffect(() => {
    let alive = true
    setLoading(true)
    const q = route === '/' ? '/' : route
    fetch(`${API}/article?route=${encodeURIComponent(q)}`)
      .then(async r => {
        if (r.status === 404) throw new Error('没有这篇文档')
        if (!r.ok) throw new Error(`正文加载失败（HTTP ${r.status}）`)
        return (await r.json()) as Article
      })
      .then(data => {
        if (!alive) return
        setArticle(data)
        setError(null)
        setLoading(false)
        // 换页回到顶部：不这么做会停在上一篇的滚动位置，看起来很怪
        window.scrollTo({ top: 0, behavior: 'auto' })
      })
      .catch(e => {
        if (!alive) return
        setArticle(null)
        setError(e instanceof Error ? e.message : String(e))
        setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [route])

  // 面包屑：由路由逐段拼出来，标题从树里查（查不到就用原文段）
  const titleByRoute = useMemo(() => {
    const map = new Map<string, string>()
    const walk = (n: TreeNode) => {
      map.set(n.route, n.title)
      n.children?.forEach(walk)
    }
    if (meta?.tree) walk(meta.tree)
    return map
  }, [meta])

  const crumbs = useMemo(() => {
    if (route === '/') return [{ title: meta?.rootTitle || '官方文档' }]
    // 只有**真有页面**的层级才做成链接：像「使用指南」这种中间层在官方文档里只是目录，
    // 点进去会 404 —— 给它做成链接就是制造悬空入口。
    const withPage = new Set(meta?.routes || [])
    const items: { title: React.ReactNode }[] = [
      {
        title: withPage.has('/') ? <a onClick={() => navigate('/docs')}>{meta?.rootTitle || '官方文档'}</a>
                                 : (meta?.rootTitle || '官方文档'),
      },
    ]
    const segs = route.split('/').filter(Boolean)
    segs.forEach((_, i) => {
      const r = '/' + segs.slice(0, i + 1).join('/') + '/'
      const label = titleByRoute.get(r) || segs[i]
      const last = i === segs.length - 1
      items.push({ title: last || !withPage.has(r) ? label : <a onClick={() => navigate(`/docs${r}`)}>{label}</a> })
    })
    return items
  }, [route, titleByRoute, meta, navigate])

  const find = useCallback(
    (el: Element | null): HTMLElement | null => {
      if (!el) return null
      const tag = el.tagName.toLowerCase()
      if (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4') return el as HTMLElement
      return el.querySelector('h1, h2, h3, h4')
    },
    []
  )

  const slug = (text: string) =>
    encodeURIComponent(
      text
        .trim()
        .toLowerCase()
        .replace(/[\s]+/g, '-')
        .replace(/[^\w\u4e00-\u9fa5-]/g, '')
    )

  const components = useMemo(() => {
    // 顶层页的正文 H1 与页头大标题是同一句话，渲染出来就是连排两行 —— 所以整段拿掉。
    // `topLevel` 由后端按路由深度给出（后端才是"哪些算顶层"的真源）。
    const dropH1 = Boolean(article?.topLevel)
    return {
      a: ({ href, children, ...rest }: any) => {
        const h: string = href || ''
        const isExternal = /^[a-z][a-z0-9+.-]*:\/\//i.test(h)
        // 站内文档链接（后端已把 .md 相对链接改写成了文档路由）
        const looksInternal = h.startsWith('/') && !h.startsWith('/static/')
        if (!isExternal && looksInternal) {
          return (
            <a
              {...rest}
              href={`/docs${h}`}
              onClick={e => {
                e.preventDefault()
                navigate(`/docs${h}`)
              }}
            >
              {children}
            </a>
          )
        }
        return (
          <a {...rest} href={h} target="_blank" rel="noreferrer">
            {children}
          </a>
        )
      },
      img: ({ src, alt, ...rest }: any) => {
        const s: string = src || ''
        if (!s || s.includes('{{')) return null // 原文里未展开的 mkdocs 宏（如 {{pipe}}），别渲染成裂图
        const resolved = s.startsWith('/') ? s : resolveAssetPath(route, s)
        return <img {...rest} src={assetUrl(resolved)} alt={alt || ''} loading="lazy" style={{ maxWidth: '100%' }} />
      },
      h1: ({ children, ...rest }: any) =>
        dropH1 ? null : (
          <Title level={2} id={slug(String(children))} {...rest}>
            {children}
          </Title>
        ),
      h2: ({ children, ...rest }: any) => (
        <Title level={3} id={slug(String(children))} {...rest}>
          {children}
        </Title>
      ),
      h3: ({ children, ...rest }: any) => (
        <Title level={4} id={slug(String(children))} {...rest}>
          {children}
        </Title>
      ),
      table: ({ children, ...rest }: any) => (
        // 手机端硬规矩：表格一律横向滚动，否则整页被撑宽（见 tools/check_mobile.py）
        <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table {...rest} style={{ borderCollapse: 'collapse', width: '100%' }}>
            {children}
          </table>
        </div>
      ),
      pre: ({ children, ...rest }: any) => (
        <pre
          {...rest}
          style={{
            background: '#f6f8fa',
            padding: 12,
            borderRadius: 6,
            overflowX: 'auto',
            maxWidth: '100%',
          }}
        >
          {children}
        </pre>
      ),
      blockquote: ({ children, ...rest }: any) => (
        <blockquote
          {...rest}
          style={{
            margin: '12px 0',
            padding: '8px 14px',
            borderLeft: '4px solid #d9d9d9',
            background: '#fafafa',
            borderRadius: 4,
          }}
        >
          {children}
        </blockquote>
      ),
    }
  }, [navigate, route, slug, article?.topLevel])

  const treeData = useMemo(() => (meta?.tree?.children ? toTreeData(meta.tree.children) : []), [meta])

  return (
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>
        <FileTextOutlined style={{ marginRight: 8 }} />
        {meta?.rootTitle || '官方文档中心'}
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        SillyTavern 官方文档的全量中文译文，共 {meta?.pages ?? '—'} 页
        {meta?.commit ? <Tag style={{ marginLeft: 8 }}>对应上游 {meta.commit.slice(0, 7)}</Tag> : null}
      </Paragraph>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* 左：目录树（窄屏收进折叠面板，点开才占位置） */}
        {isMobile ? (
          <Collapse
            style={{ width: '100%' }}
            activeKey={tocOpen ? ['toc'] : []}
            onChange={keys => setTocOpen(keys.length > 0)}
            items={[
              {
                key: 'toc',
                label: (
                  <span>
                    <UnorderedListOutlined style={{ marginRight: 6 }} />
                    目录（共 {meta?.pages ?? '—'} 页）
                  </span>
                ),
                children: (
                  <div style={{ maxHeight: '52vh', overflow: 'auto' }}>
                    <Tree
                      treeData={treeData}
                      defaultExpandedKeys={treeData.map(d => d.key as string)}
                      selectedKeys={[route]}
                      onSelect={keys => {
                        const k = keys[0] as string | undefined
                        setTocOpen(false) // 选完就收起来，把正文让出来
                        if (k && k !== route) navigate(`/docs${k}`)
                      }}
                    />
                  </div>
                ),
              },
            ]}
          />
        ) : (
          <Card
            size="small"
            title="目录"
            style={{ width: 280, flex: '0 0 auto', position: 'sticky', top: 12 }}
            styles={{ body: { maxHeight: '68vh', overflow: 'auto', padding: '8px 4px' } }}
          >
            {treeData.length ? (
              <Tree
                treeData={treeData}
                // 只默认展开 5 个大类：全展开会把 89 个节点拉成一条长表，第一眼反而找不到入口；
                // 选中的那篇若在折叠的分支里，用户点一下箭头就看到了（跳转链路不受影响）。
                defaultExpandedKeys={treeData.map(d => d.key as string)}
                selectedKeys={[route]}
                onSelect={(keys) => {
                  const k = keys[0] as string | undefined
                  if (k && k !== route) navigate(`/docs${k}`)
                }}
              />
            ) : (
              <div style={{ padding: 8 }}>
                <Spin size="small" />
              </div>
            )}
          </Card>
        )}

        {/* 右：正文 */}
        <div style={{ flex: '1 1 480px', minWidth: 0 }}>
          <Breadcrumb items={crumbs} style={{ marginBottom: 8 }} />
          <Card size="small" styles={{ body: { padding: '16px 20px' } }}>
            {error ? (
              <Alert
                type="warning"
                showIcon
                message={error}
                description={
                  error.includes('尚未生成')
                    ? '服务端还没生成文档产物：在项目根执行 python tools/gen_docs_zh.py 后刷新本页。'
                    : undefined
                }
              />
            ) : loading && !article ? (
              <div style={{ textAlign: 'center', padding: '48px 0' }}>
                <Spin />
              </div>
            ) : article ? (
              <div className="docs-body">
                {article.synthetic && article.route !== '/' ? (
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="本节索引页"
                    description="这篇是导航用的索引（官方原文里这一节没有独立页面），下面列出本节包含的页面。"
                  />
                ) : null}
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={components}>
                  {article.content}
                </ReactMarkdown>
              </div>
            ) : (
              <Empty description="没有这篇文档" />
            )}
          </Card>

          {article?.source ? (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
              <LinkOutlined /> 原文：SillyTavern-Docs/{article.source}
            </Text>
          ) : null}
        </div>
      </div>
    </div>
  )
}
