const api = require('../../utils/api')
const config = require('../../utils/config')
const { requireAuth } = require('../../utils/session')
const { money } = require('../../utils/format')
const { resolveCityImage } = require('../../utils/travel-assets')

const DAY_THEMES = [
  { dot: '#2d7657', bg: '#f4faf6', border: '#d9eee2' },
  { dot: '#d4744c', bg: '#fef8f5', border: '#f2dbd0' },
  { dot: '#4c7cb0', bg: '#f5f8fc', border: '#d0dff2' },
  { dot: '#9b7c4c', bg: '#faf8f3', border: '#e8ddc4' },
  { dot: '#5c8a6f', bg: '#f4f9f5', border: '#d0e6d6' },
  { dot: '#8c5c7a', bg: '#f9f5f8', border: '#e2d0dc' },
]

function stepIcon(segment) {
  const s = segment.toLowerCase()
  if (/吃|餐|火锅|面|粉|汤|小吃|烤|美食|饭店|餐厅|串|肉|虾|蟹|鱼|鸡|鸭|牛|羊|猪|兔/.test(s)) return 'eat'
  if (/寺|庙|祠|堂|塔|教堂|博物|文化|历史|古|遗址/.test(s)) return 'culture'
  if (/逛|街|巷|路|市|步行|散步|溜达|漫步|骑行|骑车/.test(s)) return 'walk'
  if (/茶|咖啡|酒|吧|馆/.test(s)) return 'cafe'
  if (/车|船|飞机|交通|地铁|公交|高铁|火车/.test(s)) return 'transport'
  if (/住|宿|酒店|民宿|客栈|入住/.test(s)) return 'hotel'
  return 'spot'
}

function splitDaySteps(text) {
  if (!text) return []
  const raw = text.split(/[→｜]/).map(s => s.trim()).filter(Boolean)
  if (raw.length <= 1) return []
  return raw.map(segment => {
    const timeMatch = segment.match(/^(早上|上午|中午|下午|傍晚|晚上|深夜|早起)/)
    const label = timeMatch ? timeMatch[1] : ''
    const icon = stepIcon(segment)
    return { label, text: segment, icon }
  })
}

function imageSrc(imageUrl) {
  if (!imageUrl) return ''
  if (/^https?:\/\//i.test(imageUrl)) return imageUrl
  return `${config.BASE_URL}/${imageUrl.replace(/^\//, '')}`
}

Page({
  data: {
    type: '',
    city: null,
    template: null,
    spots: [],
    foods: [],
    loading: true,
    error: ''
  },

  onLoad() {
    if (!requireAuth()) return
    const raw = wx.getStorageSync('oneclick_trip_preview_item')
    wx.removeStorageSync('oneclick_trip_preview_item')
    if (!raw || !raw.type) {
      wx.showToast({ title: '页面参数缺失', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ type: raw.type })
    if (raw.type === 'city') this.loadCity(raw)
    else if (raw.type === 'template') this.loadTemplate(raw)
  },

  async loadCity(raw) {
    this.setData({ loading: true, error: '' })
    try {
      const [city, spots, foods] = await Promise.all([
        api.city(raw.id),
        api.spots(raw.id),
        api.foods(raw.id)
      ])
      this.setData({
        city: {
          ...city,
          coverUrl: raw.imageUrl || resolveCityImage(city.name, city.id),
          seasonText: city.bestSeason || '全年皆宜',
          province: city.province || ''
        },
        spots: (spots || []).slice(0, 6).map(spot => ({
          ...spot,
          imageSrc: imageSrc(spot.imageUrl),
          priceLabel: Number(spot.ticketPrice) ? `¥${spot.ticketPrice}` : '免费',
          ratingLabel: spot.rating ? `${spot.rating} 分` : ''
        })),
        foods: (foods || []).slice(0, 6).map(food => ({
          ...food,
          imageSrc: imageSrc(food.imageUrl),
          priceLabel: `人均 ¥${food.avgPrice || '--'}`,
          category: food.category || '本地特色'
        }))
      })
    } catch (error) {
      this.setData({ error: error.message || '加载失败' })
    } finally {
      this.setData({ loading: false })
    }
  },

  loadTemplate(raw) {
    const summary = raw.summary || ''
    const dayBlocks = summary.split(/(?=Day\d+)/g).filter(Boolean)
    const planDays = dayBlocks.map((block, index) => {
      const cleaned = block.replace(/^Day\d+\s*/g, '').replace(/^[：:]\s*/, '').trim()
      const steps = splitDaySteps(cleaned)
      const theme = DAY_THEMES[index % DAY_THEMES.length]
      return { dayIndex: index + 1, label: `第 ${index + 1} 天`, text: cleaned, steps, theme }
    })
    if (!planDays.length && summary) {
      const steps = splitDaySteps(summary)
      planDays.push({ dayIndex: 1, label: '行程概览', text: summary, steps, theme: DAY_THEMES[0] })
    }
    const tplCover = raw.coverUrl || resolveCityImage(raw.title, raw.cityId)
    const tplDays = raw.days || planDays.length || 3
    this.setData({
      loading: false,
      template: {
        ...raw,
        coverUrl: tplCover,
        paceLabel: raw.pace === 'COMPACT' ? '紧凑' : '舒适节奏',
        budgetLabel: raw.budgetLevel === 'HIGH' ? '高预算' : raw.budgetLevel === 'LOW' ? '省着玩' : '预算适中',
        planDays
      }
    })
  },

  goBack() {
    wx.navigateBack({ fail: () => wx.switchTab({ url: '/pages/home/index' }) })
  },

  onSpotImageError(event) {
    const index = event.currentTarget.dataset.index
    if (index == null) return
    this.setData({ [`spots[${index}].imageSrc`]: '' })
  },

  onFoodImageError(event) {
    const index = event.currentTarget.dataset.index
    if (index == null) return
    this.setData({ [`foods[${index}].imageSrc`]: '' })
  },

  startAiForCity() {
    const city = this.data.city
    if (!city) return
    wx.setStorageSync('oneclick_trip_pending_prompt', `帮我规划一次${city.name}旅行。目的地是${city.name}，${city.seasonText}适合游玩。请围绕${city.name}安排行程。`)
    wx.switchTab({ url: '/pages/ai/index' })
  },

  startAiForTemplate() {
    const tpl = this.data.template
    if (!tpl) return
    const dest = (tpl.title || '').replace(/[0-9]+日.*$/, '').trim() || '目的地'
    wx.setStorageSync('oneclick_trip_pending_prompt', `帮我规划一次${dest}旅行。参考这${tpl.days || 3}天行程：${tpl.title}，${tpl.paceLabel || ''}节奏，${tpl.budgetLabel || ''}预算。`)
    wx.switchTab({ url: '/pages/ai/index' })
  }
})
