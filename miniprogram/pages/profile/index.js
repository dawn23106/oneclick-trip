const api = require('../../utils/api')
const { requireAuth, getSavedUser, clearSession } = require('../../utils/session')

function withInitial(user) {
  const safeUser = user || {}
  const name = safeUser.nickname || safeUser.username || '旅行者'
  return {
    ...safeUser,
    displayName: name,
    initial: name.slice(0, 1),
    hasRemoteAvatar: /^https?:\/\//.test(safeUser.avatarUrl || '')
  }
}

Page({
  data: {
    user: withInitial(getSavedUser()),
    stats: { trips: 0, conversations: 0 },
    loading: true,
    showEdit: false,
    editForm: { nickname: '', avatarUrl: '' },
    saving: false,
    error: ''
  },

  onShow() {
    if (!requireAuth()) return
    this.loadProfile()
  },

  async onPullDownRefresh() {
    await this.loadProfile()
    wx.stopPullDownRefresh()
  },

  async loadProfile() {
    this.setData({ loading: true, error: '' })
    try {
      const [profile, trips, conversations] = await Promise.all([
        api.me(),
        api.tripPlans().catch(() => []),
        api.conversations().catch(() => [])
      ])
      const user = withInitial(profile)
      wx.setStorageSync('oneclick_trip_user', user)
      const app = getApp()
      app.globalData.user = user
      this.setData({
        user,
        stats: { trips: (trips || []).length, conversations: (conversations || []).length }
      })
    } catch (error) {
      this.setData({ error: error.message || '资料加载失败' })
    } finally {
      this.setData({ loading: false })
    }
  },

  openEdit() {
    this.setData({
      showEdit: true,
      editForm: { nickname: this.data.user.nickname || '', avatarUrl: this.data.user.avatarUrl || '' },
      error: ''
    })
  },

  closeEdit() {
    if (!this.data.saving) this.setData({ showEdit: false })
  },

  onEditInput(event) {
    this.setData({ [`editForm.${event.currentTarget.dataset.field}`]: event.detail.value, error: '' })
  },

  async saveProfile() {
    const nickname = this.data.editForm.nickname.trim()
    if (!nickname) {
      this.setData({ error: '昵称不能为空' })
      return
    }
    this.setData({ saving: true, error: '' })
    try {
      const profile = await api.updateProfile({ nickname, avatarUrl: this.data.editForm.avatarUrl.trim() })
      const user = withInitial(profile)
      wx.setStorageSync('oneclick_trip_user', user)
      getApp().globalData.user = user
      this.setData({ user, showEdit: false })
      wx.showToast({ title: '资料已更新', icon: 'success' })
    } catch (error) {
      this.setData({ error: error.message || '保存失败' })
    } finally {
      this.setData({ saving: false })
    }
  },

  goTrips() {
    wx.switchTab({ url: '/pages/trips/index' })
  },

  goAi() {
    wx.switchTab({ url: '/pages/ai/index' })
  },

  openBookings() {
    wx.navigateTo({
      url: '/pages/bookings/index',
      fail: () => wx.showToast({ title: '暂时无法打开预订清单', icon: 'none' })
    })
  },

  showAbout() {
    wx.showModal({
      title: '关于一键游',
      content: '一键游把零散的旅行想法整理成清晰、可执行的完整行程。当前版本为项目演示版。',
      showCancel: false,
      confirmColor: '#267254'
    })
  },

  logout() {
    wx.showModal({
      title: '退出登录？',
      content: '退出后，本机将清除登录状态。',
      confirmColor: '#c84c43',
      success(result) {
        if (!result.confirm) return
        clearSession()
        wx.reLaunch({ url: '/pages/login/index' })
      }
    })
  }
})
