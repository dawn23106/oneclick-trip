function dateLabel(value) {
  if (!value) return '日期待定'
  const date = value instanceof Date ? value : new Date(String(value).replace(/-/g, '/'))
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function timeLabel(value) {
  if (!value) return ''
  const date = value instanceof Date ? value : new Date(String(value).replace(/-/g, '/'))
  if (Number.isNaN(date.getTime())) return value
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  return `${date.getMonth() + 1}/${date.getDate()}`
}

function money(value, currency = 'CNY') {
  const number = Number(value)
  if (!Number.isFinite(number)) return '预算待定'
  const symbol = currency === 'CNY' ? '¥' : `${currency} `
  return `${symbol}${Math.round(number).toLocaleString()}`
}

function greeting() {
  const hour = new Date().getHours()
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

module.exports = { dateLabel, timeLabel, money, greeting }
