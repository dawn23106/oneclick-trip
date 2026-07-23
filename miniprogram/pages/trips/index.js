const api = require('../../utils/api')
const { requireAuth } = require('../../utils/session')
const { dateLabel, money } = require('../../utils/format')
const { resolveCityImage } = require('../../utils/travel-assets')

function tripState(startDate, days) {
  if (!startDate) return 'PLANNING'
  const start = new Date(`${startDate}T00:00:00`)
  const end = new Date(start)
  end.setDate(end.getDate() + Math.max(Number(days || 1) - 1, 0))
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (today < start) return 'UPCOMING'
  if (today > end) return 'PAST'
  return 'ACTIVE'
}

Page({
  data: {
    trips: [],
    visibleTrips: [],
    filter: 'ALL',
    loading: true,
    error: '',
    filters: [
      { key: 'ALL', label: '全部' },
      { key: 'UPCOMING', label: '待出发' },
      { key: 'PAST', label: '已结束' }
    ]
  },

  onShow() {
    if (!requireAuth()) return
    this.loadTrips()
  },

  async onPullDownRefresh() {
    await this.loadTrips()
    wx.stopPullDownRefresh()
  },

  async loadTrips() {
    this.setData({ loading: true, error: '' })
    try {
      const list = await api.tripPlans()
      const trips = (list || []).map((item, index) => {
        const state = tripState(item.startDate, item.days)
        const statusMap = {
          UPCOMING: '待出发', ACTIVE: '旅行中', PAST: '已结束', PLANNING: '规划中'
        }
        return {
          ...item,
          state,
          statusLabel: statusMap[state],
          dateText: item.startDate ? `${dateLabel(item.startDate)} · ${item.days || '?'}天` : `${item.days || '?'}天 · 日期待定`,
          budgetText: money(item.totalBudget, item.currency),
          sourceLabel: item.planType === 'AI' ? 'AI 智能规划' : '基础路线',
          coverUrl: resolveCityImage(item.destination),
          coverClass: `cover-${index % 4}`
        }
      })
      this.setData({ trips }, () => this.applyFilter())
    } catch (error) {
      this.setData({ error: error.message || '行程加载失败' })
    } finally {
      this.setData({ loading: false })
    }
  },

  setFilter(event) {
    this.setData({ filter: event.currentTarget.dataset.key }, () => this.applyFilter())
  },

  applyFilter() {
    const { trips, filter } = this.data
    const visibleTrips = filter === 'ALL'
      ? trips
      : trips.filter(item => filter === 'UPCOMING'
        ? ['UPCOMING', 'ACTIVE', 'PLANNING'].includes(item.state)
        : item.state === 'PAST')
    this.setData({ visibleTrips })
  },

  openTrip(event) {
    const { id, type } = event.currentTarget.dataset
    wx.navigateTo({ url: `/pages/trip-detail/index?id=${id}&type=${type}` })
  },

  createTrip() {
    wx.switchTab({ url: '/pages/ai/index' })
  }
})
