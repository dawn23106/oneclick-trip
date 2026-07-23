const api = require('../../utils/api')
const { create: createBookingDraft } = require('../../utils/booking-api')
const { requireAuth } = require('../../utils/session')
const { money, dateLabel } = require('../../utils/format')
const { resolveCityImage } = require('../../utils/travel-assets')

const ITEM_TYPE_LABELS = {
  SPOT: '景点',
  FOOD: '美食',
  HOTEL: '住宿',
  TRANSPORT: '交通',
  ACTIVITY: '体验'
}

function itemTypeLabel(value) {
  const key = String(value || '').toUpperCase()
  return ITEM_TYPE_LABELS[key] || value || '安排'
}

function normalizeRule(data) {
  return {
    conversationId: '',
    planId: '',
    version: 0,
    bookableOptions: [],
    title: data.title,
    destination: data.cityName,
    coverUrl: resolveCityImage(data.cityName, data.cityId),
    summary: data.summary,
    days: data.days,
    people: data.peopleCount,
    startDate: data.startDate,
    budgetText: money(data.totalBudget),
    sourceLabel: data.sourceType === 'AI' ? 'AI 智能规划' : '基础路线',
    dayPlans: (data.dayPlans || []).map(day => ({
      dayNo: day.dayNo,
      title: day.title || `第 ${day.dayNo} 天`,
      summary: day.summary || '',
      items: (day.items || []).map(item => ({
        title: item.title,
        description: item.description || '',
        address: item.address || '',
        time: [item.startTime, item.endTime].filter(Boolean).join(' - '),
        typeLabel: itemTypeLabel(item.itemType),
        costText: Number(item.cost) ? money(item.cost) : ''
      }))
    }))
  }
}

function normalizeAi(data) {
  const plan = data.plan || {}
  const entities = data.entities || {}
  const days = plan.days || []
  const selected = data.selectedOptions || {}
  const bookableOptions = [
    ...(selected.hotel_option_ids || []).map(optionId => ({ optionId, bookingType: 'hotel' })),
    ...(selected.transport_option_ids || []).map(optionId => ({ optionId, bookingType: 'transport' })),
    ...(selected.ticket_option_ids || []).map(optionId => ({ optionId, bookingType: 'ticket' }))
  ].filter(item => item.optionId)
  return {
    conversationId: data.conversationId || '',
    planId: data.planId || plan.plan_id || '',
    version: data.version || plan.version || 1,
    bookableOptions,
    title: `${plan.destination || entities.destination || '旅行'} ${days.length} 天智能行程`,
    destination: plan.destination || entities.destination || '本次旅行',
    coverUrl: resolveCityImage(plan.destination || entities.destination),
    summary: Array.isArray(plan.assumptions) ? plan.assumptions.join('；') : (plan.summary || '由 AI 多阶段规划生成。'),
    days: days.length,
    people: entities.people || 1,
    startDate: entities.start_date || '',
    budgetText: money(plan.total_cost, plan.currency),
    sourceLabel: `AI 智能规划 · V${data.version || 1}`,
    dayPlans: days.map((day, dayIndex) => ({
      dayNo: day.day_index || dayIndex + 1,
      title: day.title || `第 ${dayIndex + 1} 天`,
      summary: day.summary || '',
      items: (day.items || []).map(item => ({
        title: item.name || item.title,
        description: item.description || '',
        address: item.address || item.location_name || item.location_id || '',
        time: String(item.start_time || item.start_at || '').slice(0, 5),
        typeLabel: itemTypeLabel(item.item_type),
        costText: Number(item.estimated_cost) ? money(item.estimated_cost, plan.currency) : '',
        optionId: item.ticket_option_id || '',
        bookingType: 'ticket'
      }))
    }))
  }
}

Page({
  data: {
    id: '',
    type: 'RULE',
    trip: null,
    activeDay: 0,
    loading: true,
    error: '',
    booking: false
  },

  onLoad(options) {
    if (!requireAuth()) return
    this.setData({ id: options.id, type: options.type || 'RULE' })
    this.loadTrip()
  },

  async onPullDownRefresh() {
    await this.loadTrip()
    wx.stopPullDownRefresh()
  },

  async loadTrip() {
    this.setData({ loading: true, error: '' })
    try {
      const data = this.data.type === 'AI' ? await api.aiTripPlan(this.data.id) : await api.tripPlan(this.data.id)
      const trip = this.data.type === 'AI' ? normalizeAi(data) : normalizeRule(data)
      trip.metaLine = [trip.startDate ? dateLabel(trip.startDate) : '日期待定', `${trip.days || 0} 天`, `${trip.people || 1} 人`].join(' · ')
      this.setData({ trip, activeDay: 0 })
      wx.setNavigationBarTitle({ title: trip.destination || '行程详情' })
    } catch (error) {
      this.setData({ error: error.message || '行程读取失败' })
    } finally {
      this.setData({ loading: false })
    }
  },

  selectDay(event) {
    this.setData({ activeDay: Number(event.currentTarget.dataset.index) })
  },

  continueWithAi() {
    wx.setStorageSync('oneclick_trip_pending_prompt', `请继续帮我优化“${this.data.trip.title}”`)
    wx.switchTab({ url: '/pages/ai/index' })
  },

  openBookings() {
    wx.navigateTo({ url: '/pages/bookings/index' })
  },

  addAllToBookings() {
    this.createBooking(this.data.trip.bookableOptions)
  },

  addItemToBookings(event) {
    const { optionId, bookingType } = event.currentTarget.dataset
    this.createBooking([{ optionId, bookingType }])
  },

  async createBooking(options) {
    const trip = this.data.trip
    if (this.data.booking) return
    if (!trip || !trip.conversationId || !trip.planId || !trip.version) {
      wx.showToast({ title: '该行程不是可预订的 AI 方案', icon: 'none' })
      return
    }
    const usable = (options || []).filter(item => item && item.optionId)
    if (!usable.length) {
      wx.showModal({
        title: '暂无可预订选项',
        content: '当前行程使用的是 AI 估价，没有供应商返回的酒店、交通或门票选项。行程仍可查看和继续优化。',
        showCancel: false,
        confirmColor: '#267254'
      })
      return
    }
    this.setData({ booking: true })
    try {
      await createBookingDraft({
        conversationId: trip.conversationId,
        planId: trip.planId,
        planVersion: trip.version,
        bookingTypes: [...new Set(usable.map(item => item.bookingType))],
        selectedOptionIds: [...new Set(usable.map(item => item.optionId))]
      })
      wx.showModal({
        title: '已加入预订清单',
        content: '预订草稿将在 15 分钟后过期，请前往清单确认。',
        confirmText: '查看清单',
        cancelText: '稍后处理',
        confirmColor: '#267254',
        success: result => {
          if (result.confirm) this.openBookings()
        }
      })
    } catch (error) {
      wx.showToast({ title: error.message || '加入失败', icon: 'none' })
    } finally {
      this.setData({ booking: false })
    }
  },

  onShareAppMessage() {
    return {
      title: this.data.trip ? this.data.trip.title : '我的一键游行程',
      path: `/pages/trip-detail/index?id=${this.data.id}&type=${this.data.type}`
    }
  }
})
