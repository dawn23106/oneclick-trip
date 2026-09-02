const api = require('../../utils/api')
const { requireAuth, getSavedUser } = require('../../utils/session')
const { greeting } = require('../../utils/format')
const { heroImage, resolveCityImage } = require('../../utils/travel-assets')

Page({
  data: {
    user: null,
    greeting: '',
    heroImage,
    prompt: '',
    locating: false,
    cities: [],
    templates: [],
    loading: true,
    error: '',
    suggestions: [
      '成都 3 天游，想吃得好一点',
      '周末去长沙，两个人预算 2000',
      '帮我规划一次轻松的亲子旅行'
    ]
  },

  onShow() {
    if (!requireAuth()) return
    const user = getSavedUser() || {}
    const displayName = user.nickname || user.username || '旅行者'
    this.setData({ user: { ...user, displayName, initial: displayName.slice(0, 1) }, greeting: greeting() })
    // Refresh the catalog on every visit so hot reload and backend data changes
    // cannot leave stale web-only asset paths in the page state.
    this.loadData()
    this.tryAutoLocation()
  },

  async onPullDownRefresh() {
    await this.loadData()
    wx.stopPullDownRefresh()
  },

  async loadData() {
    this.setData({ loading: true, error: '' })
    try {
      const [cities, templates] = await Promise.all([api.cities(), api.templates()])
      this.setData({
        cities: (cities || []).slice(0, 6).map((item, index) => ({
          ...item,
          imageUrl: resolveCityImage(item.name, item.id),
          initial: String(item.name || '旅').slice(0, 1),
          toneClass: `tone-${index % 3}`
        })),
        templates: (templates || []).slice(0, 6).map(item => ({
          ...item,
          coverUrl: resolveCityImage(item.title, item.cityId),
          paceLabel: item.pace === 'COMPACT' ? '紧凑' : '舒适',
          budgetLabel: item.budgetLevel === 'HIGH' ? '高预算' : item.budgetLevel === 'LOW' ? '省着玩' : '预算适中'
        }))
      })
    } catch (error) {
      this.setData({ error: error.message || '内容加载失败' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onPrompt(event) {
    this.setData({ prompt: event.detail.value })
  },

  useSuggestion(event) {
    this.startAi(event.currentTarget.dataset.text)
  },

  submitPrompt() {
    this.startAi(this.data.prompt)
  },

  tryAutoLocation() {
    // tab 页会反复触发 onShow；每个页面实例只自动尝试一次，避免频繁定位。
    if (this.autoLocationAttempted) return
    this.autoLocationAttempted = true
    wx.getSetting({
      success: result => {
        const locationPermission = result.authSetting['scope.userLocation']
        // 未选择过时会由 getLocation 拉起首次授权；已授权时直接自动定位。
        // 明确拒绝过则保持安静，用户仍可通过页面按钮主动重新开启。
        if (locationPermission !== false) this.locateCurrentCity(false)
      }
    })
  },

  useCurrentLocation() {
    this.locateCurrentCity(true)
  },

  locateCurrentCity(interactive) {
    if (this.data.locating) return
    this.setData({ locating: true })
    wx.getLocation({
      type: 'wgs84',
      isHighAccuracy: false,
      success: async position => {
        try {
          const location = await api.reverseLocation(position.latitude, position.longitude)
          this.setData({ prompt: prependOrigin(this.data.prompt, location.city) })
          wx.showToast({ title: `已定位到${location.city}`, icon: 'success' })
        } catch (error) {
          wx.showToast({ title: error.message || '城市识别失败，请手动填写', icon: 'none' })
        } finally {
          this.setData({ locating: false })
        }
      },
      fail: error => {
        this.setData({ locating: false })
        if (isLocationPermissionDenied(error)) {
          if (!interactive) {
            wx.showToast({ title: '未开启定位，可点击“使用当前位置”重新授权', icon: 'none' })
            return
          }
          wx.showModal({
            title: '需要定位权限',
            content: '定位仅用于识别出发城市；也可以直接在输入框中手动填写。',
            confirmText: '去设置',
            success: result => {
              if (!result.confirm) return
              wx.openSetting({
                success: setting => {
                  if (setting.authSetting['scope.userLocation']) this.locateCurrentCity(false)
                }
              })
            }
          })
          return
        }
        wx.showToast({ title: '定位失败，请手动填写出发城市', icon: 'none' })
      }
    })
  },

  startCity(event) {
    const city = this.data.cities[event.currentTarget.dataset.index]
    if (!city) return
    wx.setStorageSync('oneclick_trip_preview_item', {
      type: 'city',
      id: city.id,
      name: city.name,
      imageUrl: city.imageUrl || '',
      summary: city.summary || '',
      bestSeason: city.bestSeason || '',
      province: city.province || ''
    })
    wx.navigateTo({ url: '/pages/preview/index' })
  },

  startTemplate(event) {
    const item = this.data.templates[event.currentTarget.dataset.index]
    if (!item) return
    wx.setStorageSync('oneclick_trip_preview_item', {
      type: 'template',
      id: item.id,
      cityId: item.cityId,
      title: item.title || '',
      days: item.days || 3,
      budgetLevel: item.budgetLevel || 'MEDIUM',
      pace: item.pace || 'RELAXED',
      summary: item.summary || '',
      coverUrl: item.coverUrl || ''
    })
    wx.navigateTo({ url: '/pages/preview/index' })
  },

  startAi(text) {
    const prompt = String(text || '').trim() || '帮我规划一次轻松的旅行'
    wx.setStorageSync('oneclick_trip_pending_prompt', prompt)
    this.setData({ prompt: '' })
    wx.switchTab({ url: '/pages/ai/index' })
  },

  goTrips() {
    wx.switchTab({ url: '/pages/trips/index' })
  }
})

function prependOrigin(message, city) {
  const content = String(message || '').replace(/^从[^，。,]{1,20}出发[，,]\s*/, '').trim()
  return `从${city}出发，${content}`
}

function isLocationPermissionDenied(error) {
  const message = String(error && error.errMsg ? error.errMsg : '').toLowerCase()
  return message.includes('auth deny')
    || message.includes('auth denied')
    || message.includes('permission denied')
    || message.includes('authorize no response')
}
