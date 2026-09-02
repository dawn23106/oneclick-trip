const api = require('../../utils/api')
const config = require('../../utils/config')
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
    currentCity: '',
    nearbyLoading: false,
    nearbyHasCatalog: false,
    nearbyCatalogCity: null,
    nearbySpots: [],
    nearbyFoods: [],
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
    const cachedCity = wx.getStorageSync('oneclick_trip_current_city') || ''
    this.setData({
      user: { ...user, displayName, initial: displayName.slice(0, 1) },
      greeting: greeting(),
      currentCity: this.data.currentCity || cachedCity
    })
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
      if (this.data.currentCity) await this.loadNearbyRecommendations(this.data.currentCity)
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
          this.setData({
            currentCity: location.city,
            prompt: prependOrigin(this.data.prompt, location.city)
          })
          wx.setStorageSync('oneclick_trip_current_city', location.city)
          await this.loadNearbyRecommendations(location.city)
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

  async loadNearbyRecommendations(cityName) {
    const currentCity = normalizeCityName(cityName)
    if (!currentCity) return
    if (!this.data.cities.length) {
      this.setData({ currentCity, nearbyLoading: true })
      return
    }

    const catalogCity = this.data.cities.find(city => normalizeCityName(city.name) === currentCity)
    if (!catalogCity) {
      this.setData({
        currentCity,
        nearbyLoading: false,
        nearbyHasCatalog: false,
        nearbyCatalogCity: null,
        nearbySpots: [],
        nearbyFoods: []
      })
      return
    }

    this.setData({ currentCity, nearbyLoading: true })
    try {
      const [spots, foods] = await Promise.all([
        api.spots(catalogCity.id),
        api.foods(catalogCity.id)
      ])
      const nearbySpots = (spots || []).slice(0, 4).map(spot => ({
        ...spot,
        imageSrc: imageSrc(spot.imageUrl),
        meta: [spot.rating ? `${spot.rating} 分` : '', Number(spot.ticketPrice) ? `¥${spot.ticketPrice}` : '免费']
          .filter(Boolean)
          .join(' · ')
      }))
      const nearbyFoods = (foods || []).slice(0, 4).map(food => ({
        ...food,
        category: food.category || '本地特色',
        priceLabel: food.avgPrice ? `人均 ¥${food.avgPrice}` : '当地特色'
      }))
      this.setData({
        nearbyLoading: false,
        nearbyHasCatalog: nearbySpots.length > 0 || nearbyFoods.length > 0,
        nearbyCatalogCity: catalogCity,
        nearbySpots,
        nearbyFoods
      })
    } catch (error) {
      this.setData({
        nearbyLoading: false,
        nearbyHasCatalog: false,
        nearbyCatalogCity: catalogCity,
        nearbySpots: [],
        nearbyFoods: []
      })
    }
  },

  openNearbyCity() {
    const city = this.data.nearbyCatalogCity
    if (!city) {
      this.startNearbyAi()
      return
    }
    wx.setStorageSync('oneclick_trip_preview_item', {
      type: 'city',
      id: city.id,
      name: city.name,
      imageUrl: city.imageUrl || resolveCityImage(city.name, city.id),
      summary: city.summary || '',
      bestSeason: city.bestSeason || '',
      province: city.province || ''
    })
    wx.navigateTo({ url: '/pages/preview/index' })
  },

  startNearbyAi() {
    const city = this.data.currentCity
    if (!city) return
    this.startAi(`我现在在${city}，请结合旅游知识库推荐适合当前城市的吃喝玩乐。分别给出值得去的景点、当地特色美食和一条轻松的半日游路线，并说明推荐理由。`)
  },

  onNearbySpotImageError(event) {
    const index = event.currentTarget.dataset.index
    if (index == null) return
    this.setData({ [`nearbySpots[${index}].imageSrc`]: '' })
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

function normalizeCityName(value) {
  return String(value || '').trim().replace(/市$/, '')
}

function imageSrc(imageUrl) {
  const value = String(imageUrl || '').trim()
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  return `${config.BASE_URL}/${value.replace(/^\//, '')}`
}

function isLocationPermissionDenied(error) {
  const message = String(error && error.errMsg ? error.errMsg : '').toLowerCase()
  return message.includes('auth deny')
    || message.includes('auth denied')
    || message.includes('permission denied')
    || message.includes('authorize no response')
}
