function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function inline(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

function markdownToHtml(markdown) {
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n')
  const output = []
  let listType = ''

  const closeList = () => {
    if (!listType) return
    output.push(`</${listType}>`)
    listType = ''
  }

  lines.forEach(raw => {
    const line = raw.trim()
    if (!line) {
      closeList()
      return
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      closeList()
      output.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`)
      return
    }
    const ordered = line.match(/^\d+[.)、]\s*(.+)$/)
    const unordered = line.match(/^[-*•]\s+(.+)$/)
    if (ordered || unordered) {
      const nextType = ordered ? 'ol' : 'ul'
      if (listType !== nextType) {
        closeList()
        listType = nextType
        output.push(`<${nextType}>`)
      }
      output.push(`<li>${inline((ordered || unordered)[1])}</li>`)
      return
    }
    closeList()
    output.push(`<p>${inline(line)}</p>`)
  })
  closeList()
  return output.join('')
}

module.exports = { markdownToHtml }
