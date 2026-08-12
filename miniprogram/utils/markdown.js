function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function inline(value) {
  // Process links [text](url) before other inline rules
  let result = escapeHtml(value)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return result
}

function markdownToHtml(markdown) {
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n')
  const output = []
  let listType = ''
  let inCodeBlock = false
  let codeBlockLines = []

  const closeList = () => {
    if (!listType) return
    output.push(`</${listType}>`)
    listType = ''
  }

  const flushCodeBlock = () => {
    if (!codeBlockLines.length) return
    output.push('<pre><code>' + codeBlockLines.join('\n') + '</code></pre>')
    codeBlockLines = []
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]
    const line = raw.trim()

    // Code block toggle
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock()
        inCodeBlock = false
      } else {
        closeList()
        inCodeBlock = true
        codeBlockLines = []
      }
      continue
    }
    if (inCodeBlock) {
      codeBlockLines.push(escapeHtml(raw))
      continue
    }

    if (!line) {
      closeList()
      continue
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,})\s*$/.test(line)) {
      closeList()
      output.push('<hr />')
      continue
    }

    // Blockquote
    if (line.startsWith('>')) {
      closeList()
      const quoteContent = line.replace(/^>\s?/, '')
      output.push('<blockquote><p>' + inline(quoteContent) + '</p></blockquote>')
      continue
    }

    // Headings
    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      closeList()
      output.push('<h' + heading[1].length + '>' + inline(heading[2]) + '</h' + heading[1].length + '>')
      continue
    }

    // Lists
    const ordered = line.match(/^\d+[.)、]\s*(.+)$/)
    const unordered = line.match(/^[-*•]\s+(.+)$/)
    if (ordered || unordered) {
      const nextType = ordered ? 'ol' : 'ul'
      if (listType !== nextType) {
        closeList()
        listType = nextType
        output.push('<' + nextType + '>')
      }
      output.push('<li>' + inline((ordered || unordered)[1]) + '</li>')
      continue
    }

    // Paragraph
    closeList()
    output.push('<p>' + inline(line) + '</p>')
  }

  closeList()
  flushCodeBlock()
  return output.join('')
}

module.exports = { markdownToHtml }
