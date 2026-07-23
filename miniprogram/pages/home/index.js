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
        templates: (templates || []).slice(0, 4).map(item => ({
          ...item,
          coverUrl: resolveCityImage(item.title, item.cityId)
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

  startCity(event) {
    const city = this.data.cities[event.currentTarget.dataset.index]
    if (city) this.startAi(`帮我规划一次${city.name}旅行`)
  },

  startTemplate(event) {
    const item = this.data.templates[event.currentTarget.dataset.index]
    if (item) this.startAi(`参考“${item.title}”，帮我规划一份适合我的行程`)
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
