
export const DEV = typeof location !== 'undefined' && location.search.includes('dev=1')

export default function TraceBar({ text }) {
  if (!DEV || !text) return null
  return <div className="trace-dev"><b>契约溯源</b>　{text}</div>
}
