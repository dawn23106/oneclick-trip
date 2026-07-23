const request = require('../../utils/request')
const { requireAuth } = require('../../utils/session')

const BOOKING_PATH = '/api/bookings'

function listBookingDrafts() {
  return request(BOOKING_PATH)
}

function confirmBookingDraft(draftId) {
  return request(`${BOOKING_PATH}/${draftId}/confirm`, { method: 'POST' })
}

function cancelBookingDraft(draftId) {
  return request(`${BOOKING_PATH}/${draftId}/cancel`, { method: 'POST' })
}

const STATUS_LABELS = {
  pending_confirmation: '待确认',
  confirmed: '已确认',
  cancelled: '已取消',
  expired: '已过期'
}

const TYPE_LABELS = {
  hotel: '酒店',
  train: '火车',
  flight: '航班',
  ticket: '门票',
  transport: '交通'
}

function formatTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).replace('T', ' ').slice(0, 16)
  const pad = number => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function decorate(item) {
  return {
    ...item,
    statusLabel: STATUS_LABELS[item.status] || item.status,
    typeText: (item.bookingTypes || []).map(type => TYPE_LABELS[type] || type).join('、') || '旅行服务',
    createdText: formatTime(item.createdAt),
    expiresText: formatTime(item.expiresAt),
    destinationText: item.destination || '旅行预订',
    optionText: (item.selectedOptionIds || []).join('、')
  }
}

Page({
  data: {
    bookings: [],
    placeholderRows: [1, 2],
    loading: true,
    error: '',
    actionId: ''
  },

  onShow() {
    if (!requireAuth()) return
    this.loadBookings()
  },

  goBack() {
    wx.navigateBack({
      fail: () => wx.switchTab({ url: '/pages/trips/index' })
    })
  },

  async onPullDownRefresh() {
    await this.loadBookings(false)
    wx.stopPullDownRefresh()
  },

  async loadBookings(showLoading = true) {
    if (showLoading) this.setData({ loading: true })
    this.setData({ error: '' })
    try {
      const bookings = await listBookingDrafts()
      this.setData({ bookings: (bookings || []).map(decorate) })
    } catch (error) {
      this.setData({ error: error.message || '预订清单读取失败，请稍后重试' })
    } finally {
      this.setData({ loading: false })
    }
  },

  confirmBooking(event) {
    const draftId = event.currentTarget.dataset.id
    wx.showModal({
      title: '确认这份预订草稿？',
      content: '当前项目会记录确认状态，不会自动扣款或向真实供应商下单。',
      confirmText: '确认',
      confirmColor: '#267254',
      success: result => {
        if (result.confirm) this.changeStatus(draftId, 'confirm')
      }
    })
  },

  cancelBooking(event) {
    const draftId = event.currentTarget.dataset.id
    wx.showModal({
      title: '取消这份预订草稿？',
      content: '取消后不能再次确认。',
      confirmText: '取消草稿',
      confirmColor: '#c84c43',
      success: result => {
        if (result.confirm) this.changeStatus(draftId, 'cancel')
      }
    })
  },

  async changeStatus(draftId, action) {
    if (this.data.actionId) return
    this.setData({ actionId: draftId })
    try {
      if (action === 'confirm') await confirmBookingDraft(draftId)
      else await cancelBookingDraft(draftId)
      wx.showToast({ title: action === 'confirm' ? '已确认' : '已取消', icon: 'success' })
      await this.loadBookings(false)
    } catch (error) {
      wx.showToast({ title: error.message || '操作失败', icon: 'none' })
    } finally {
      this.setData({ actionId: '' })
    }
  }
})
